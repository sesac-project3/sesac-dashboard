"""S3 배경 영상 → 숏폼(긍정 1건 + 부정 1건 / 종목) 자동 생성 파이프라인.

종목(stocks.id 오름차순 = PRODUCT.md 매핑 순서) × [긍정, 부정] 조합마다:
  1. S3에 `{종목명}_positive|negative.mp4`가 있는지 확인 — 없으면 그 조합은 건너뜀
  2. sentiment_analysis에서 원하는 감성과 일치하는 가장 최근 날짜를 찾는다.
     해당 (날짜, 종목) 행이 비어 있으면 그날 data_source(뉴스) 헤드라인으로
     LLM 감성분류를 해서 그 자리에서 채워 넣는다 (PRD §7.4 배치를 on-demand로 구현).
  3. 그 날짜의 뉴스(source_type='뉴스') 헤드라인으로 자막을 LLM 생성
  4. report_service.get_stock_report() 결과 + 같은 뉴스 헤드라인으로 3줄 AI Insight 생성
  5. shortforms에 upsert (UNIQUE(stock_id, sentiment, published_date))

근거 데이터(뉴스/리포트)가 없으면 절대 지어내지 않고 조용히 건너뛴다 (PRD §9.3 환각 방지).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Literal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.common.openai_client import get_openai_client
from app.common.s3 import get_shortform_video_url
from app.domain.reports.schemas import StockReport
from app.domain.reports.service import report_service
from app.domain.shortforms.models import Shortform as ShortformModel
from app.domain.stocks.models import Stock

logger = logging.getLogger(__name__)

Sentiment = Literal["긍정", "부정"]
LOOKBACK_DAYS = 30  # 실데이터 보유 기간(2026-07-11~08-10, 약 30일)을 한 번에 훑는다


def _news_headlines(db: Session, stock_id: int, target_date: date, source_type: str = "뉴스") -> list[str]:
    rows = db.execute(
        text("""
            SELECT headline FROM data_source
            WHERE stock_id = :stock_id AND date = :target_date AND source_type = :source_type
            ORDER BY id
        """),
        {"stock_id": stock_id, "target_date": target_date, "source_type": source_type},
    ).fetchall()
    return [r.headline for r in rows]


def _distinct_news_dates(db: Session, stock_id: int, limit_days: int = LOOKBACK_DAYS) -> list[date]:
    rows = db.execute(
        text("""
            SELECT DISTINCT date FROM data_source
            WHERE stock_id = :stock_id AND source_type = '뉴스'
            ORDER BY date DESC LIMIT :limit_days
        """),
        {"stock_id": stock_id, "limit_days": limit_days},
    ).fetchall()
    return [r.date for r in rows]


def classify_daily_sentiment(headlines: list[str]) -> str | None:
    """그날 뉴스 헤드라인들을 보고 '긍정'/'부정'/'중립' 중 하나로 분류. 키 없거나 실패하면 None
    (없는 감성을 지어내지 않고 그 날짜는 건너뛴다)."""
    client = get_openai_client()
    if client is None or not headlines:
        return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 한국 주식 뉴스 헤드라인을 보고 하루치 종목 여론을 "
                        "'긍정', '부정', '중립' 중 하나로만 분류하는 애널리스트야. "
                        "다른 말은 절대 하지 말고 단어 하나만 출력해."
                    ),
                },
                {
                    "role": "user",
                    "content": "오늘 이 종목 뉴스 헤드라인:\n"
                    + "\n".join(f"- {h}" for h in headlines[:20]),
                },
            ],
            max_tokens=10,
        )
        text_out = (response.choices[0].message.content or "").strip()
        for label in ("긍정", "부정", "중립"):
            if label in text_out:
                return label
        return None
    except Exception:
        logger.exception("감성 분류 LLM 호출 실패")
        return None


def ensure_sentiment_analysis(db: Session, stock_id: int, target_date: date) -> str | None:
    """sentiment_analysis에 (날짜, 종목) 행이 있으면 그대로, 없으면 그날 뉴스로 분류해서
    채워 넣고 반환한다. 그날 뉴스가 아예 없으면 None."""
    row = db.execute(
        text("SELECT sentiment FROM sentiment_analysis WHERE stock_id = :stock_id AND date = :target_date"),
        {"stock_id": stock_id, "target_date": target_date},
    ).fetchone()
    if row:
        return row.sentiment

    sentiment = classify_daily_sentiment(_news_headlines(db, stock_id, target_date))
    if sentiment is None:
        return None

    db.execute(
        text("""
            INSERT INTO sentiment_analysis (date, stock_id, sentiment)
            VALUES (:target_date, :stock_id, :sentiment)
            ON CONFLICT (date, stock_id) DO NOTHING
        """),
        {"target_date": target_date, "stock_id": stock_id, "sentiment": sentiment},
    )
    db.commit()
    return sentiment


def find_date_with_sentiment(db: Session, stock_id: int, target_sentiment: Sentiment) -> date | None:
    for candidate in _distinct_news_dates(db, stock_id):
        if ensure_sentiment_analysis(db, stock_id, candidate) == target_sentiment:
            return candidate
    return None


def generate_subtitle(stock_name: str, sentiment: Sentiment, headlines: list[str]) -> str:
    fallback = f"{stock_name}, 오늘 {sentiment} 분위기"
    client = get_openai_client()
    if client is None or not headlines:
        return fallback
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 주식 숏폼 영상에 붙는 한 줄 자막을 쓰는 카피라이터야. "
                        "아래 뉴스 헤드라인에 없는 사실은 절대 지어내지 말고, "
                        "25자 내외 구어체 캡션 한 줄만 출력해 (따옴표/불릿 없이). "
                        "한글/영문/숫자/기본 문장부호만 쓰고 한자(漢字)는 절대 섞지 마."
                    ),
                },
                {
                    "role": "user",
                    "content": f"종목: {stock_name}\n오늘 분위기: {sentiment}\n뉴스 헤드라인:\n"
                    + "\n".join(f"- {h}" for h in headlines[:10]),
                },
            ],
            max_tokens=80,
        )
        line = (response.choices[0].message.content or "").strip().splitlines()
        cleaned = re.sub(r"^[-*•\"']\s*", "", line[0]).strip() if line else ""
        return cleaned or fallback
    except Exception:
        logger.exception("자막 LLM 생성 실패")
        return fallback


def generate_ai_insight(
    stock_name: str, sentiment: Sentiment, report: StockReport | None, headlines: list[str]
) -> str | None:
    """3줄 고정 포맷: ① 변동성 유무(성장/감소) ② 뉴스 기반 이유 ③ 흐름 지속 여부 여론.
    근거(리포트/뉴스)가 하나도 없으면 지어내지 않고 None."""
    client = get_openai_client()
    if client is None:
        return None

    report_facts = []
    if report:
        if report.revenueTrend:
            report_facts.append(f"매출 추세: {report.revenueTrend}")
        if report.operatingProfitTrend:
            report_facts.append(f"영업이익 추세: {report.operatingProfitTrend}")
        if report.judgement:
            report_facts.append(f"AI 투자판단: {report.judgement}")
        if report.currentPrice and report.week52High and report.week52Low:
            report_facts.append(
                f"현재가 {report.currentPrice:,.0f}원 "
                f"(52주 밴드 {report.week52Low:,.0f}~{report.week52High:,.0f}원)"
            )
        if report.valuationComment:
            report_facts.append(f"밸류에이션 코멘트: {report.valuationComment}")

    if not report_facts and not headlines:
        return None

    system = (
        "너는 주식 숏폼 영상의 'AI Insight' 3줄 요약을 쓰는 애널리스트야. "
        "아래 [리포트 데이터]와 [뉴스 헤드라인]에 없는 사실·수치·기사는 절대 지어내지 마. "
        "정보가 부족하면 '데이터 근거가 제한적'이라고만 언급해.\n"
        "반드시 한국어로 정확히 3줄만 출력하고 각 줄은 '- '로 시작해:\n"
        "1번째 줄: 해당 종목의 변동성 유무를 '성장' 또는 '감소' 중 하나로 명시\n"
        "2번째 줄: 그 변동의 이유를 제공된 뉴스 헤드라인에서 실제로 언급된 이슈로만 서술\n"
        "3번째 줄: 이 흐름이 이어질지에 대한 긍정/부정 여론을 명시\n"
        "세 줄 모두 완전한 문장으로 쓰고(단어 하나만 쓰지 마), 각 줄은 40자 내외로 간결하게. "
        "한자(漢字)는 절대 섞지 마.\n"
        "예시:\n- 삼성전자의 변동성은 성장 추세입니다.\n- 반도체 수출 호조 뉴스가 주요 이슈로 작용했습니다.\n"
        "- 이 흐름이 이어질 것이라는 긍정적인 여론이 우세합니다."
    )
    user = (
        f"종목: {stock_name}\n오늘 분위기: {sentiment}\n\n"
        "[리포트 데이터]\n" + ("\n".join(report_facts) if report_facts else "(없음)") + "\n\n"
        "[뉴스 헤드라인]\n"
        + ("\n".join(f"- {h}" for h in headlines[:10]) if headlines else "(없음)")
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=300,
        )
        text_out = (response.choices[0].message.content or "").strip()
        lines = [re.sub(r"^[-*•]\s*", "", ln).strip() for ln in text_out.splitlines() if ln.strip()]
        lines = lines[:3]
        return "\n".join(lines) if len(lines) == 3 else None
    except Exception:
        logger.exception("AI Insight LLM 생성 실패")
        return None


def generate_shortform_for(db: Session, stock: Stock, sentiment: Sentiment) -> ShortformModel | None:
    video_url = get_shortform_video_url(stock.name, sentiment)
    if not video_url:
        logger.info("S3에 %s %s 영상 없음 — 건너뜀", stock.name, sentiment)
        return None

    target_date = find_date_with_sentiment(db, stock.id, sentiment)
    if target_date is None:
        logger.info("%s에 %s 감성과 일치하는 날짜 없음 — 건너뜀", stock.name, sentiment)
        return None

    headlines = _news_headlines(db, stock.id, target_date)
    subtitle = generate_subtitle(stock.name, sentiment, headlines)
    report = report_service.get_stock_report(db, stock.code)
    ai_insight = generate_ai_insight(stock.name, sentiment, report, headlines)

    row = db.scalar(
        select(ShortformModel).where(
            ShortformModel.stock_id == stock.id,
            ShortformModel.sentiment == sentiment,
            ShortformModel.published_date == target_date,
        )
    )
    if row:
        row.video_url, row.subtitle_text, row.ai_insight = video_url, subtitle, ai_insight
    else:
        row = ShortformModel(
            stock_id=stock.id,
            sentiment=sentiment,
            video_url=video_url,
            subtitle_text=subtitle,
            ai_insight=ai_insight,
            published_date=target_date,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return row


def generate_all_shortforms(db: Session) -> list[ShortformModel]:
    """종목(id 순) × [긍정, 부정] 순서대로 순회하며 생성/갱신. S3 영상이나 해당 감성 날짜가
    없는 조합은 조용히 건너뛴다."""
    stocks = db.scalars(select(Stock).order_by(Stock.id)).all()
    results = []
    for stock in stocks:
        for sentiment in ("긍정", "부정"):
            row = generate_shortform_for(db, stock, sentiment)
            if row:
                results.append(row)
    return results
