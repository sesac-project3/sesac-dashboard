"""F-03-1 7대 신호 스코어링 엔진(calculate_stock_opinion)의 total_score 컷오프를
DB 실데이터로 백테스트하고, 목표 정확도(기본 70%)를 만족하는 컷오프를 그리드서치로 찾는다.

사용법:
    .venv/bin/python scripts/backtest_scoring.py            # 현재 컷오프 정확도만 리포트
    .venv/bin/python scripts/backtest_scoring.py --tune      # 그리드서치로 컷오프 튜닝 후 비교

방법론(READ ME 먼저):
- 각 종목 x 각 거래일 T에서, "T 시점까지의 데이터만" 사용해 7대 신호를 계산한다(미래 데이터
  참조 금지 = look-ahead bias 방지). 뉴스/커뮤니티 감성은 T 기준 과거 7일 윈도우 집계.
  (주의: 현재 service.py의 실서비스 쿼리는 날짜 필터 없이 data_source 전체를 집계한다 —
  이건 "실시간 신호"라기보다 누적 스냅샷이라 백테스트 그대로 못 씀. 여기서는 point-in-time으로
  올바르게 윈도우를 잘라 씀. 실서비스 코드도 같은 문제가 있다면 별도로 고쳐야 함.)
- PER/PBR은 pykrx 실시간 조회가 이 환경에서 막혀있어(KRX 펀더멘털 엔드포인트가 빈 응답을
  반환 — 네트워크 자체는 정상) PEER_FALLBACKS 상수를 그대로 썼다. 원래 서비스 코드도 pykrx
  실패 시 이 상수로 폴백하므로 실제 운영 동작과 크게 다르지 않다. PER/PBR은 대형주 기준
  2주 안에 거의 안 변하는 값이라 신호 품질에 미치는 영향도 작다.
- "정답"(실제 등락) 라벨은 T 시점 종가 대비 T+10거래일(~2주) 종가 등락률로 정의:
    ratio >= +MOVE_THRESHOLD  -> UP   (모델이 BUY라고 했어야 정답)
    ratio <= -MOVE_THRESHOLD  -> DOWN (모델이 SELL이라고 했어야 정답)
    그 사이                    -> FLAT (모델이 HOLD라고 했어야 정답)
- 종목이 5개뿐이고 뉴스/커뮤니티 데이터가 1개월치(2026-07-11~08-10)뿐이라 표본이 작다
  (통상 60~70개). 이 규모의 튜닝 결과는 통계적으로 약하다 — 참고용 캘리브레이션이지
  일반화 보장은 아니다. 표본이 늘면(데이터 축적/종목 확대) 재실행해서 재튜닝할 것.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.domain.reports.peer_service import PEER_FALLBACKS
from app.domain.reports.scoring import calculate_stock_opinion

# 라벨링 기준 등락률(%) — 10거래일 기준 개별종목 변동폭 분포를 보고 정한 값(스크립트 실행 시
# 분포를 같이 출력한다). 모델을 이 값에 맞춰 끼워 맞추지 않도록 정답 정의는 그리드서치 대상에서
# 제외했다 — 튜닝 대상은 아래 total_score 컷오프뿐.
MOVE_THRESHOLD_PCT = 3.0
HORIZON_TRADING_DAYS = 10  # ~2주
SENTIMENT_WINDOW_DAYS = 7


@dataclass
class Sample:
    stock_code: str
    as_of: date
    opinion: str
    total_score: float
    forward_return_pct: float
    actual_label: str  # UP / FLAT / DOWN


def label_actual(return_pct: float) -> str:
    if return_pct >= MOVE_THRESHOLD_PCT:
        return "UP"
    if return_pct <= -MOVE_THRESHOLD_PCT:
        return "DOWN"
    return "FLAT"


def is_correct(opinion: str, actual: str) -> bool:
    return (
        (opinion == "BUY" and actual == "UP")
        or (opinion == "SELL" and actual == "DOWN")
        or (opinion == "HOLD" and actual == "FLAT")
    )


def opinion_from_score(score: float, buy_cutoff: float, sell_cutoff: float) -> str:
    if score >= buy_cutoff:
        return "BUY"
    if score < sell_cutoff:
        return "SELL"
    return "HOLD"


def build_samples() -> list[Sample]:
    engine = create_engine(settings.database_url)
    samples: list[Sample] = []

    with engine.connect() as conn:
        stocks = conn.execute(text("SELECT id, code FROM stocks ORDER BY id")).fetchall()

        for stock in stocks:
            candles = conn.execute(
                text(
                    """
                    SELECT trade_date, close_price, high_price, low_price
                    FROM stock_daily_candles
                    WHERE stock_id = :sid
                    ORDER BY trade_date ASC
                    """
                ),
                {"sid": stock.id},
            ).fetchall()
            if len(candles) < 40:
                continue
            dates = [c.trade_date for c in candles]

            fin = conn.execute(
                text(
                    """
                    SELECT operating_margin FROM financial_statements
                    WHERE stock_id = :sid ORDER BY fiscal_year DESC LIMIT 1
                    """
                ),
                {"sid": stock.id},
            ).fetchone()
            operating_margin = float(fin.operating_margin) if fin and fin.operating_margin is not None else None

            fallback = PEER_FALLBACKS.get(stock.code)
            per_val = fallback[0].per if fallback else None
            pbr_val = fallback[0].pbr if fallback else None

            # T 후보: 앞뒤로 52주밴드용 과거 데이터 + 10거래일 뒤 정답 데이터가 있어야 함
            for i in range(20, len(dates) - HORIZON_TRADING_DAYS):
                as_of = dates[i]

                news_rows = conn.execute(
                    text(
                        """
                        SELECT sentiment, COUNT(*) as cnt FROM data_source
                        WHERE stock_id = :sid AND source_type = '뉴스'
                          AND date > :start AND date <= :end
                        GROUP BY sentiment
                        """
                    ),
                    {"sid": stock.id, "start": as_of - timedelta(days=SENTIMENT_WINDOW_DAYS), "end": as_of},
                ).fetchall()
                news_counts = {str(r.sentiment).lower(): int(r.cnt) for r in news_rows if r.sentiment}
                if not news_counts:
                    continue  # 이 윈도우에 뉴스/커뮤니티 데이터가 아직 없는 T는 건너뜀(표본 왜곡 방지)

                comm_rows = conn.execute(
                    text(
                        """
                        SELECT sentiment, COUNT(*) as cnt FROM data_source
                        WHERE stock_id = :sid AND source_type = '토스_커뮤니티'
                          AND date > :start AND date <= :end
                        GROUP BY sentiment
                        """
                    ),
                    {"sid": stock.id, "start": as_of - timedelta(days=SENTIMENT_WINDOW_DAYS), "end": as_of},
                ).fetchall()
                comm_counts = {str(r.sentiment).lower(): int(r.cnt) for r in comm_rows if r.sentiment}

                window = candles[max(0, i - 251) : i + 1][::-1]  # 최신순, 최대 252일
                high_prices = [float(c.high_price) for c in window]
                low_prices = [float(c.low_price) for c in window]
                current_price = float(candles[i].close_price)
                week52_high = max(high_prices)
                week52_low = min(low_prices)

                daily_candles = [{"close_price": float(c.close_price)} for c in candles[max(0, i - 59) : i + 1][::-1]]

                opinion, _qual, total_score = calculate_stock_opinion(
                    news_sentiment_counts=news_counts,
                    community_sentiment_counts=comm_counts,
                    operating_margin=operating_margin,
                    per=per_val,
                    pbr=pbr_val,
                    week52_high=week52_high,
                    week52_low=week52_low,
                    current_price=current_price,
                    daily_candles=daily_candles,
                )

                future_price = float(candles[i + HORIZON_TRADING_DAYS].close_price)
                forward_return_pct = (future_price / current_price - 1.0) * 100.0
                actual = label_actual(forward_return_pct)

                samples.append(
                    Sample(
                        stock_code=stock.code,
                        as_of=as_of,
                        opinion=opinion,
                        total_score=total_score,
                        forward_return_pct=forward_return_pct,
                        actual_label=actual,
                    )
                )

    return samples


def accuracy(samples: list[Sample], buy_cutoff: float, sell_cutoff: float) -> float:
    if not samples:
        return 0.0
    correct = 0
    for s in samples:
        opinion = opinion_from_score(s.total_score, buy_cutoff, sell_cutoff)
        if is_correct(opinion, s.actual_label):
            correct += 1
    return correct / len(samples) * 100.0


def grid_search(samples: list[Sample], target_pct: float = 70.0) -> tuple[float, float, float]:
    best = (0.45, -0.30, accuracy(samples, 0.45, -0.30))  # 현재 운영값을 기준선으로 시작
    for buy_cutoff in [round(x * 0.05, 2) for x in range(-10, 21)]:  # -0.50 ~ 1.00
        for sell_cutoff in [round(x * 0.05, 2) for x in range(-20, 7)]:  # -1.00 ~ 0.30
            if sell_cutoff >= buy_cutoff:
                continue
            acc = accuracy(samples, buy_cutoff, sell_cutoff)
            if acc > best[2]:
                best = (buy_cutoff, sell_cutoff, acc)
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true", help="그리드서치로 컷오프 튜닝")
    args = parser.parse_args()

    samples = build_samples()
    print(f"표본 수: {len(samples)}개 (종목 {len({s.stock_code for s in samples})}개)")
    if not samples:
        print("표본이 없습니다 — DB에 데이터가 충분한지 확인하세요.")
        return

    returns = sorted(s.forward_return_pct for s in samples)
    print(
        f"10거래일 등락률 분포: min={returns[0]:.1f}% p25={returns[len(returns)//4]:.1f}% "
        f"median={returns[len(returns)//2]:.1f}% p75={returns[3*len(returns)//4]:.1f}% max={returns[-1]:.1f}%"
    )
    label_counts = {label: sum(1 for s in samples if s.actual_label == label) for label in ("UP", "FLAT", "DOWN")}
    print(f"실제 라벨 분포(±{MOVE_THRESHOLD_PCT}% 기준): {label_counts}")

    base_acc = accuracy(samples, 0.45, -0.30)
    print(f"\n현재 컷오프(BUY>=0.45, SELL<-0.30) 정확도: {base_acc:.1f}%")

    if args.tune:
        buy_cutoff, sell_cutoff, acc = grid_search(samples)
        print(f"\n튜닝 결과: BUY>={buy_cutoff}, SELL<{sell_cutoff} -> 정확도 {acc:.1f}%")
        if acc >= 70.0:
            print("목표 70% 달성.")
        else:
            print("목표 70% 미달 — 표본 규모/기간 확장이 필요할 수 있음.")


if __name__ == "__main__":
    main()
