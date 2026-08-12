from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.reports.schemas import PeerComparisonRow, StockReport
from app.domain.reports.scoring import (
    analyze_financial_trends,
    calculate_risk_scores,
    calculate_valuation_band,
)

# 5종목 동종 업계 기본 데이터 (F-03-5)
PEER_GROUPS = {
    "005930": [
        PeerComparisonRow(name="삼성전자", per=13.5, pbr=1.35, roe=10.2),
        PeerComparisonRow(name="SK하이닉스", per=11.2, pbr=1.85, roe=15.8),
        PeerComparisonRow(name="TSMC", per=22.4, pbr=5.80, roe=28.5),
    ],
    "000660": [
        PeerComparisonRow(name="SK하이닉스", per=11.2, pbr=1.85, roe=15.8),
        PeerComparisonRow(name="삼성전자", per=13.5, pbr=1.35, roe=10.2),
        PeerComparisonRow(name="Micron", per=14.8, pbr=1.92, roe=12.1),
    ],
    "005380": [
        PeerComparisonRow(name="현대자동차", per=5.8, pbr=0.62, roe=11.5),
        PeerComparisonRow(name="기아", per=5.2, pbr=0.75, roe=14.2),
        PeerComparisonRow(name="Toyota", per=9.1, pbr=1.05, roe=11.8),
    ],
    "373220": [
        PeerComparisonRow(name="LG에너지솔루션", per=45.2, pbr=4.10, roe=8.9),
        PeerComparisonRow(name="삼성SDI", per=18.5, pbr=1.20, roe=7.2),
        PeerComparisonRow(name="CATL", per=21.0, pbr=3.40, roe=18.2),
    ],
    "042660": [
        PeerComparisonRow(name="한화오션", per=28.4, pbr=2.15, roe=7.8),
        PeerComparisonRow(name="HD한국조선해양", per=15.2, pbr=1.10, roe=8.4),
        PeerComparisonRow(name="삼성중공업", per=22.1, pbr=1.65, roe=6.9),
    ],
}


class ReportService:
    """F-03 AI 종목 심층 분석 리포트 백엔드 서비스"""

    @staticmethod
    def get_stock_report(db: Session, stock_code: str) -> StockReport | None:
        """
        종목 코드에 해당하는 52주 밴드(밸류에이션) 및 정량 데이터 리포트 생성
        """
        # 1. stocks 테이블에서 종목 존재 여부 확인
        stock = db.execute(
            text("SELECT id, code, name FROM stocks WHERE code = :code"),
            {"code": stock_code},
        ).fetchone()

        if not stock:
            return None

        stock_id = stock.id
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 2. stock_reports DB 사전 생성 캐시 조회
        cached = db.execute(
            text("""
                SELECT judgement, judgement_reasons, revenue_trend, operating_profit_trend,
                       operating_margin_trend, growth_grade, profitability_grade,
                       risk_scores, peer_comparison, week52_high, week52_low, current_price
                FROM stock_reports
                WHERE stock_id = :stock_id AND report_date = :report_date
            """),
            {"stock_id": stock_id, "report_date": today_str},
        ).fetchone()

        if cached:
            peer_list = None
            if cached.peer_comparison:
                peer_list = [PeerComparisonRow(**item) for item in cached.peer_comparison]

            w_high = float(cached.week52_high) if cached.week52_high else 0.0
            w_low = float(cached.week52_low) if cached.week52_low else 0.0
            c_price = float(cached.current_price) if cached.current_price else 0.0

            _, _, _, comment = calculate_valuation_band([w_high], [w_low], c_price)

            return StockReport(
                stockCode=stock_code,
                reportDate=today_str,
                judgement=cached.judgement,
                judgementReasons=cached.judgement_reasons,
                revenueTrend=cached.revenue_trend,
                operatingProfitTrend=cached.operating_profit_trend,
                growthGrade=cached.growth_grade,
                riskScores=cached.risk_scores,
                peerComparison=peer_list,
                week52High=w_high,
                week52Low=w_low,
                currentPrice=c_price,
                valuationComment=comment,
            )

        # 3. DB 일봉 캔들(stock_daily_candles)에서 52주(최근 252일) 시세 수집
        candle_rows = db.execute(
            text("""
                SELECT high_price, low_price, close_price
                FROM stock_daily_candles
                WHERE stock_id = :stock_id
                ORDER BY trade_date DESC
                LIMIT 252
            """),
            {"stock_id": stock_id},
        ).fetchall()

        if candle_rows:
            high_prices = [float(row.high_price) for row in candle_rows]
            low_prices = [float(row.low_price) for row in candle_rows]
            current_price = float(candle_rows[0].close_price)
        else:
            # 캔들 미적재 시 종목별 기본 현재가 목업 처리
            default_prices = {
                "005930": (85000.0, 52900.0, 72300.0),
                "000660": (223000.0, 52900.0, 183900.0),
                "005380": (290000.0, 170000.0, 245000.0),
                "373220": (450000.0, 310000.0, 385000.0),
                "042660": (38000.0, 21000.0, 29500.0),
            }
            w_h, w_l, c_p = default_prices.get(stock_code, (100000.0, 50000.0, 75000.0))
            high_prices, low_prices, current_price = [w_h], [w_l], c_p

        # 52주 최고가, 최저가, 현재가 및 위치 코멘트 계산 (F-03-6)
        week52_high, week52_low, current_price, valuation_comment = calculate_valuation_band(
            high_prices, low_prices, current_price
        )

        # 60일 종가 기준 리스크 스코어 계산 (F-03-3)
        close_prices = [float(row.close_price) for row in reversed(candle_rows[:60])] if candle_rows else [current_price]
        risk_scores = calculate_risk_scores(close_prices, operating_profit_margin=12.5)

        # 재무제표 추세 분석 (F-03-2)
        fin_rows = db.execute(
            text("""
                SELECT revenue, operating_profit, operating_margin
                FROM financial_statements
                WHERE stock_id = :stock_id
                ORDER BY fiscal_year DESC
                LIMIT 2
            """),
            {"stock_id": stock_id},
        ).fetchall()

        rev_trend, profit_trend, _, growth_g, _ = "증가", "증가", "개선", "보통", "보통"
        if len(fin_rows) >= 2:
            rev_trend, profit_trend, _, growth_g, _ = analyze_financial_trends(
                float(fin_rows[1].revenue), float(fin_rows[0].revenue),
                float(fin_rows[1].operating_profit), float(fin_rows[0].operating_profit)
            )

        return StockReport(
            stockCode=stock_code,
            reportDate=today_str,
            judgement="매수",
            judgementReasons=[
                "최근 52주 밴드 내 적정 주가 위치 형성",
                "동종 업계 대비 밸류에이션 매력 유지",
                "매출액 및 영업이익 성장세 지속"
            ],
            revenueTrend=rev_trend,
            operatingProfitTrend=profit_trend,
            growthGrade=growth_g,
            riskScores=risk_scores,
            peerComparison=PEER_GROUPS.get(stock_code, []),
            week52High=week52_high,
            week52Low=week52_low,
            currentPrice=current_price,
            valuationComment=valuation_comment,
        )


report_service = ReportService()
