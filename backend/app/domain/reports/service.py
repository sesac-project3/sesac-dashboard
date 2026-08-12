from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.reports.schemas import FinancialRow, PeerComparisonRow, StockReport
from app.domain.reports.schemas import FinancialRow, PeerComparisonRow, StockReport, NewsItem
from app.domain.reports.scoring import (
    analyze_financial_trends,
    calculate_risk_scores,
    calculate_valuation_band,
)

def extract_publisher(url: str | None) -> str:
    if not url:
        return "주요 언론사"
    if "mk.co.kr" in url:
        return "매일경제"
    if "hankyung.com" in url:
        return "한국경제"
    if "chosun.com" in url:
        return "조선비즈"
    if "etnews.com" in url:
        return "전자신문"
    if "mt.co.kr" in url:
        return "머니투데이"
    if "enewstoday.co.kr" in url:
        return "이뉴스투데이"
    if "goodkyung.com" in url:
        return "굿모닝경제"
    return "주요 언론사"


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
        종목 코드에 해당하는 52주 밴드(밸류에이션), 5년치 재무 시계열 및 정량 데이터 리포트 생성
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
                operatingMarginTrend=cached.operating_margin_trend,
                growthGrade=cached.growth_grade,
                profitabilityGrade=cached.profitability_grade,
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

        # 4. DB financial_statements 에서 최근 5년치 수치 수집 (F-03-2)
        fin_rows = db.execute(
            text("""
                SELECT fiscal_year, revenue, operating_profit, operating_margin
                FROM financial_statements
                WHERE stock_id = :stock_id
                ORDER BY fiscal_year DESC
                LIMIT 5
            """),
            {"stock_id": stock_id},
        ).fetchall()

        # 차트용 5년치 시계열 (연도 오름차순: 과거 -> 최신)
        financials = [
            FinancialRow(
                fiscalYear=int(row.fiscal_year),
                revenue=float(row.revenue),
                operatingProfit=float(row.operating_profit),
                operatingMargin=float(row.operating_margin),
            )
            for row in reversed(fin_rows)
        ]

        # 5. 최신 뉴스 및 감성 라벨 수집 (F-03-4): 긍정, 부정, 중립 감성 우선 조합 후 3개 보충
        news_rows = db.execute(
            text("""
                SELECT d.id, d.headline, d.url, d.created_at,
                       COALESCE(s.sentiment, '중립') AS sentiment
                FROM data_source d
                LEFT JOIN sentiment_analysis s
                       ON d.stock_id = s.stock_id AND DATE(d.created_at) = s.date
                WHERE d.stock_id = :stock_id AND d.source_type = '뉴스'
                ORDER BY d.created_at DESC
                LIMIT 30
            """),
            {"stock_id": stock_id},
        ).fetchall()

        selected_rows = []
        used_ids = set()

        # A. 긍정, 부정, 중립 1개씩 우선 수집
        for target_sent in ["긍정", "부정", "중립"]:
            for r in news_rows:
                if r.id not in used_ids and r.sentiment == target_sent:
                    selected_rows.append(r)
                    used_ids.add(r.id)
                    break

        # B. 긍정/부정/중립 중 없는 감성이 있다면 최신순으로 추가 채워서 3개 보장
        if len(selected_rows) < 3:
            for r in news_rows:
                if r.id not in used_ids:
                    selected_rows.append(r)
                    used_ids.add(r.id)
                    if len(selected_rows) == 3:
                        break

        latest_news = []
        now = datetime.now(timezone.utc)
        for row in selected_rows:
            diff_hours = max(1, int((now - row.created_at.replace(tzinfo=timezone.utc)).total_seconds() // 3600)) if row.created_at else 2
            sent_label = row.sentiment if row.sentiment in ["긍정", "부정", "중립"] else "중립"
            
            raw_headline = str(row.headline or "").strip()
            clean_title = raw_headline.split("\n")[0][:75] + ("..." if len(raw_headline) > 75 else "")
            pub_name = extract_publisher(row.url)

            latest_news.append(
                NewsItem(
                    id=int(row.id),
                    title=clean_title,
                    publisher=pub_name,
                    publishedAt=f"{diff_hours}시간 전",
                    sentiment=sent_label,
                    url=row.url,
                )
            )


        if not latest_news:
            latest_news = DEFAULT_NEWS.get(stock_code, [])

        latest_opm = float(fin_rows[0].operating_margin) if fin_rows else 10.0

        # 60일 종가 기준 리스크 스코어 계산 (F-03-3)
        close_prices = [float(row.close_price) for row in reversed(candle_rows[:60])] if candle_rows else [current_price]
        risk_scores = calculate_risk_scores(close_prices, operating_profit_margin=latest_opm)

        rev_trend, profit_trend, margin_trend, growth_g, profit_g = "증가", "증가", "개선", "보통", "보통"
        if len(fin_rows) >= 2:
            rev_trend, profit_trend, margin_trend, growth_g, profit_g = analyze_financial_trends(
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
            operatingMarginTrend=margin_trend,
            growthGrade=growth_g,
            profitabilityGrade=profit_g,
            financials=financials,
            latestNews=latest_news,
            riskScores=risk_scores,
            peerComparison=PEER_GROUPS.get(stock_code, []),
            week52High=week52_high,
            week52Low=week52_low,
            currentPrice=current_price,
            valuationComment=valuation_comment,
        )


report_service = ReportService()
