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
