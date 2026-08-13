import math
from typing import Literal

def calculate_valuation_band(
    high_prices: list[float],
    low_prices: list[float],
    current_price: float
) -> tuple[float, float, float, str]:
    """
    F-03-6 밸류에이션 분석 (52주 최고/최저가 및 현재가 위치 코멘트 계산)
    반환: (week52_high, week52_low, current_price, valuation_comment)
    """
    if not high_prices or not low_prices:
        # 캔들 데이터 부족 시 기본값 반환
        return current_price * 1.2, current_price * 0.8, current_price, "52주 밴드 데이터 수집 중입니다."

    week52_high = max(high_prices)
    week52_low = min(low_prices)

    if week52_high == week52_low:
        ratio = 50.0
    else:
        ratio = ((current_price - week52_low) / (week52_high - week52_low)) * 100

    # 52주 밴드 위치에 따른 구간별 코멘트 자동 생성
    if ratio >= 80.0:
        comment = "52주 밴드 상단 부근으로 단기 기대가 주가에 상당 부분 반영된 구간입니다."
    elif ratio >= 40.0:
        comment = "52주 밴드 중간 구간으로 적정 주가 범위 내에서 거래되고 있습니다."
    else:
        comment = "52주 밴드 하단 부근으로 최근 주가 조정이 진행되어 가격 부담이 적은 구간입니다."

    return round(week52_high, 2), round(week52_low, 2), round(current_price, 2), comment


def calculate_volatility_score(daily_close_prices: list[float]) -> float:
    """
    60일 일봉 종가 시계열 기반 수익률 표준편차(시장변동성 0~100 스코어) 계산.
    """
    if len(daily_close_prices) < 2:
        return 50.0

    returns = [
        (daily_close_prices[i] - daily_close_prices[i - 1]) / daily_close_prices[i - 1]
        for i in range(1, len(daily_close_prices))
    ]

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance)

    annualized_vol = std_dev * math.sqrt(252) * 100
    score = min(100.0, max(0.0, annualized_vol * 1.67))
    return round(score, 1)


def calculate_risk_scores(
    daily_close_prices: list[float],
    operating_profit_margin: float | None = None
) -> dict[str, float]:
    """
    F-03-3 리스크 체크 3개 축 점수 (0~100) 산출.
    """
    volatility = calculate_volatility_score(daily_close_prices)

    if operating_profit_margin is not None:
        reliability = min(100.0, max(20.0, 50.0 + operating_profit_margin * 2.5))
    else:
        reliability = 70.0

    competition = 65.0

    return {
        "시장변동성": volatility,
        "실적신뢰도": round(reliability, 1),
        "경쟁강도": round(competition, 1)
    }


def analyze_financial_trends(
    prev_revenue: float,
    curr_revenue: float,
    prev_operating_profit: float,
    curr_operating_profit: float
) -> tuple[Literal["증가", "감소"], Literal["증가", "감소"], Literal["개선", "악화"], Literal["양호", "보통", "낮음"], Literal["양호", "보통", "낮음"]]:
    """
    F-03-2 매출/영업이익 분석 및 등급 판정.
    """
    revenue_trend: Literal["증가", "감소"] = "증가" if curr_revenue >= prev_revenue else "감소"
    profit_trend: Literal["증가", "감소"] = "증가" if curr_operating_profit >= prev_operating_profit else "감소"

    prev_margin = (prev_operating_profit / prev_revenue * 100) if prev_revenue > 0 else 0
    curr_margin = (curr_operating_profit / curr_revenue * 100) if curr_revenue > 0 else 0
    margin_trend: Literal["개선", "악화"] = "개선" if curr_margin >= prev_margin else "악화"

    growth_rate = ((curr_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    if growth_rate >= 10.0:
        growth_grade: Literal["양호", "보통", "낮음"] = "양호"
    elif growth_rate >= 0.0:
        growth_grade = "보통"
    else:
        growth_grade = "낮음"

    if curr_margin >= 15.0:
        profitability_grade: Literal["양호", "보통", "낮음"] = "양호"
    elif curr_margin >= 5.0:
        profitability_grade = "보통"
    else:
        profitability_grade = "낮음"

    return revenue_trend, profit_trend, margin_trend, growth_grade, profitability_grade


def calculate_stock_opinion(
    news_sentiment_counts: dict[str, int],
    community_sentiment_counts: dict[str, int],
    operating_margin: float | None,
    per: float | None,
    pbr: float | None,
    week52_high: float | None,
    week52_low: float | None,
    current_price: float | None,
    daily_candles: list[dict] | None = None,
) -> tuple[str, str, float]:
    """
    F-03-1 다면적 7대 신호 조합 스코어링 엔진 (_stock_opinion)
    반환: (opinion, qualitative_signal, total_score)
    """
    score = 0.0

    # 1. 뉴스 신호 (news_signal: +0.6 ~ -0.6)
    n_pos = news_sentiment_counts.get("positive", 0)
    n_neg = news_sentiment_counts.get("negative", 0)
    n_tot = n_pos + n_neg + news_sentiment_counts.get("neutral", 0)
    if n_tot > 0:
        n_ratio = (n_pos - n_neg) / n_tot
        score += n_ratio * 0.6

    # 2. 커뮤니티 신호 (community_signal: +0.3 ~ -0.3)
    c_pos = community_sentiment_counts.get("positive", 0)
    c_neg = community_sentiment_counts.get("negative", 0)
    c_tot = c_pos + c_neg + community_sentiment_counts.get("neutral", 0)
    if c_tot > 0:
        c_ratio = (c_pos - c_neg) / c_tot
        score += c_ratio * 0.3

    # 3. 수익성 신호 (margin_signal)
    if operating_margin is not None:
        if operating_margin >= 30.0:
            score += 0.9
        elif operating_margin >= 15.0:
            score += 0.5
        elif operating_margin <= 0.0:
            score -= 0.7

    # 4. 밸류에이션 신호 (valuation_signal)
    if per is not None and per > 0:
        if per <= 12.0:
            score += 0.8
        elif per >= 25.0:
            score -= 0.6
    if pbr is not None and pbr > 0:
        if pbr <= 1.0:
            score += 0.7
        elif pbr <= 1.5:
            score += 0.4
        elif pbr >= 3.5:
            score -= 0.5

    # 5. 52주 주가 위치 신호 (band_signal)
    if week52_high and week52_low and current_price and week52_high > week52_low:
        pos_ratio = (current_price - week52_low) / (week52_high - week52_low)
        if pos_ratio <= 0.35:
            score += 0.8
        elif pos_ratio >= 0.75:
            score -= 0.6

    # 6. 차트/기술적 신호 & 7. 변동성 감점
    if daily_candles and len(daily_candles) >= 20:
        c_curr = float(daily_candles[0].get("close_price", 0)) if isinstance(daily_candles[0], dict) else float(getattr(daily_candles[0], "close_price", 0))
        c_20 = float(daily_candles[19].get("close_price", 0)) if isinstance(daily_candles[19], dict) else float(getattr(daily_candles[19], "close_price", 0))
        if c_20 > 0 and c_curr >= c_20 * 1.05:
            score += 0.4
        close_list = [float(c.get("close_price", 0)) if isinstance(c, dict) else float(getattr(c, "close_price", 0)) for c in daily_candles[:60]]
        vol_score = calculate_volatility_score(close_list)
        if vol_score >= 85.0:
            score -= 0.4

    total_score = round(score, 2)

    # total_score 구간에 따른 의견 및 정성적 신호 세분화
    if total_score >= 0.45:
        opinion = "BUY"
        qualitative_signal = "지표들이 양호한 편입니다"
    elif total_score >= 0.15:
        opinion = "HOLD"
        qualitative_signal = "중립적 관망 구간입니다"
    elif total_score >= -0.30:
        opinion = "HOLD"
        qualitative_signal = "혼조된 신호를 보이고 있습니다"
    else:
        opinion = "SELL"
        qualitative_signal = "부담스러운 구간입니다"

    return opinion, qualitative_signal, total_score


def generate_investment_summary(
    stock_name: str,
    current_price: float | None,
    opinion: str,
    qualitative_signal: str,
    news_items: list[dict] | None = None,
    operating_margin: float | None = None,
) -> str:
    """
    자본시장법 규제 준수 정성적 자연어 요약 생성기 (_investment_summary)
    - 종목별 정량 데이터(영업이익률 등)와 뉴스 흐름을 차별화되게 결합
    - 행동 권유 및 "전략", "권장", "비중 조절" 키워드 전면 배제
    """
    price_str = f"현재가 {current_price:,.0f}원 기준 " if current_price else ""
    opm_str = f"영업이익률({operating_margin:.1f}%) " if operating_margin is not None else ""

    news_summary = ""
    if news_items and len(news_items) > 0:
        first_title = str(news_items[0].get("title", "") if isinstance(news_items[0], dict) else getattr(news_items[0], "title", "")).strip()
        if first_title:
            news_summary = f"최근 이슈로는 '{first_title[:35]}...' 등이 확인되며, "

    if opinion == "BUY":
        summary = f"{price_str}{opm_str}수익성 및 주요 지표 흐름이 우수하여 {qualitative_signal}. {news_summary}업종 내 상대적 퀀트 매력도가 유지되는 상태입니다."
    elif opinion == "SELL":
        summary = f"{price_str}단기 변동성 및 밸류에이션 여건으로 인해 {qualitative_signal}. {news_summary}리스크 관리가 요구되는 상태입니다."
    elif qualitative_signal == "중립적 관망 구간입니다":
        summary = f"{price_str}{opm_str}실적 흐름과 주가 밴드 위치를 감안할 때 {qualitative_signal}. {news_summary}시장 재평가 추이를 지켜보는 단계입니다."
    else:
        summary = f"{price_str}주요 퀀트 지표 및 수급 신호가 {qualitative_signal}. {news_summary}시장 상황을 다각도로 관찰하는 흐름을 보이고 있습니다."

    return summary


def build_comprehensive_reasons(
    opinion: str,
    per: float | None = None,
    pbr: float | None = None,
    week52_high: float | None = None,
    week52_low: float | None = None,
    current_price: float | None = None,
    operating_margin: float | None = None,
    revenue_trend: str | None = None,
    volatility_score: float | None = None,
) -> list[str]:
    """
    F-03-1: 리포트 하단 2번~6번 섹션 수치(PER, 52주 주가위치, 영업이익률, 매출추세, 변동성 점수)를
    종합 분석하여 최종 종합 판단(opinion: BUY/HOLD/SELL)과 100% 모순 없이 일치하는 Top 3 이유 문장 동적 생성.
    """
    reasons = []

    # 1. 밸류에이션 / PER 신호 (5번 동종업계 섹션)
    if per is not None and per > 0:
        if opinion == "SELL" and per >= 25.0:
            reasons.append(f"PER {per:.1f}배 수준으로 단기 밸류에이션 평가 부담 존재")
        elif opinion == "BUY" and per <= 15.0:
            reasons.append(f"PER {per:.1f}배 수준으로 동종 업계 대비 밸류에이션 매력 확보")
        else:
            reasons.append(f"PER {per:.1f}배 수준으로 업계 적정 밸류에이션 범위 유지")

    # 2. 52주 주가 위치 신호 (6번 52주위치 섹션)
    if week52_high and week52_low and current_price and week52_high > week52_low:
        pos_ratio = ((current_price - week52_low) / (week52_high - week52_low)) * 100
        if opinion == "SELL" and pos_ratio >= 75.0:
            reasons.append(f"주가가 52주 밴드 상단부({pos_ratio:.0f}%)에 위치해 단기 차익실현 유의")
        elif opinion == "BUY" and pos_ratio <= 35.0:
            reasons.append(f"52주 밴드 하단부({pos_ratio:.0f}%) 구간 진입으로 주가 가격 부담 완화")
        else:
            reasons.append(f"52주 밴드 중간({pos_ratio:.0f}%) 구간 내 적정 주가 위치 형성")

    # 3. 실적 & 영업이익률/성장성 신호 (2번 성장성 섹션)
    if operating_margin is not None:
        if opinion == "BUY" and operating_margin >= 15.0:
            reasons.append(f"영업이익률({operating_margin:.1f}%) 우수로 견조한 실적 및 수익성 지지")
        elif opinion == "SELL" and operating_margin < 12.0:
            reasons.append(f"영업이익률({operating_margin:.1f}%) 감안 시 성장 모멘텀 관찰 필요")
        else:
            reasons.append(f"매출액 및 영업이익 성장세 지속 (영업이익률 {operating_margin:.1f}%)")
    elif revenue_trend:
        reasons.append(f"연간 매출액 {revenue_trend} 추세 반영")

    # 4. 변동성 / 리스크 체크 신호 (3번 리스크 섹션) - 3개 보장용
    if len(reasons) < 3:
        if volatility_score is not None and volatility_score >= 70.0:
            reasons.append(f"시장 변동성 점수({volatility_score:.0f}점) 확대에 따른 리스크 관리 필요")
        elif opinion == "SELL":
            reasons.append("단기 시장 변동성 확대로 인한 리스크 관리 필요")
        elif opinion == "HOLD":
            reasons.append("시장 수급 상황 및 단기 이슈 재평가 방향성 관찰 필요")
        else:
            reasons.append("주요 수급 및 퀀트 지표 개선 흐름 지속")

    return reasons[:3]


