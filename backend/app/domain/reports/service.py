import re
from datetime import datetime, timezone
import ftfy
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.reports.schemas import FinancialRow, PeerComparisonRow, StockReport, NewsItem
from app.domain.reports.scoring import (
    analyze_financial_trends,
    calculate_risk_scores,
    calculate_valuation_band,
    calculate_stock_opinion,
    generate_investment_summary,
    build_comprehensive_reasons,
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


def sanitize_headline(text_str: str) -> str:
    if not text_str:
        return text_str
    line = text_str.split('\n')[0].strip()
    fixed = ftfy.fix_text(line)
    clean = re.sub(r'[^a-zA-Z0-9가-힣ㄱ-ㅎㅏ-ㅣ\u4e00-\u9fff\s\[\]\(\)\'\"“”‘’\-–—~!?.,:;%+/·…☆★▶▷▲▼※○●□■◇◆<>&]+', '', fixed)
    # Truncate orphaned question mark fragments (e.g. ' ? ')
    clean = re.sub(r'\s+[\?\!]\s+.*$', '', clean)
    clean = re.sub(r'\s+오늘$', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean if clean else fixed




def classify_sentiment(headline: str, db_sentiment: str | None) -> str:
    if db_sentiment in ["긍정", "부정", "중립"]:
        return db_sentiment
    h = headline or ""
    pos_keywords = ["상승", "대박", "수혜", "성공", "급증", "호재", "견인", "확대", "주도", "안정", "개선", "성장", "입성", "급등"]
    neg_keywords = ["부족", "최악", "우려", "하락", "둔화", "침체", "손실", "위기", "무너지", "한계", "후폭풍"]
    if any(kw in h for kw in pos_keywords) and not any(kw in h for kw in neg_keywords):
        return "긍정"
    if any(kw in h for kw in neg_keywords):
        return "부정"
    return "중립"



# 5종목 동종 업계 기본 데이터 (F-03-5)
PEER_GROUPS = {
    "005930": [
        PeerComparisonRow(name="삼성전자", per=18.27, pbr=1.87, roe=10.85, operating_margin=14.8),
        PeerComparisonRow(name="SK하이닉스", per=13.78, pbr=8.30, roe=44.15, operating_margin=52.0),
        PeerComparisonRow(name="TSMC", per=32.34, pbr=10.48, roe=39.97, operating_margin=40.0),
    ],
    "000660": [
        PeerComparisonRow(name="SK하이닉스", per=13.78, pbr=8.30, roe=44.15, operating_margin=52.0),
        PeerComparisonRow(name="삼성전자", per=18.27, pbr=1.87, roe=10.85, operating_margin=14.8),
        PeerComparisonRow(name="Micron", per=19.49, pbr=9.84, roe=66.64, operating_margin=22.5),
    ],
    "005380": [
        PeerComparisonRow(name="현대자동차", per=12.44, pbr=0.92, roe=8.41, operating_margin=7.4),
        PeerComparisonRow(name="기아", per=7.56, pbr=0.85, roe=12.92, operating_margin=11.2),
        PeerComparisonRow(name="Toyota", per=8.48, pbr=0.95, roe=11.70, operating_margin=9.8),
    ],
    "373220": [
        PeerComparisonRow(name="LG에너지솔루션", per=-80.38, pbr=4.27, roe=-5.1, operating_margin=1.8),
        PeerComparisonRow(name="삼성SDI", per=-106.14, pbr=2.15, roe=-2.02, operating_margin=2.3),
        PeerComparisonRow(name="CATL", per=34.55, pbr=4.47, roe=24.77, operating_margin=14.5),
    ],
    "042660": [
        PeerComparisonRow(name="한화오션", per=18.90, pbr=4.24, roe=22.59, operating_margin=6.6),
        PeerComparisonRow(name="HD한국조선해양", per=10.36, pbr=1.92, roe=17.78, operating_margin=5.2),
        PeerComparisonRow(name="삼성중공업", per=35.77, pbr=4.64, roe=13.74, operating_margin=4.1),
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

        if cached and cached.current_price is not None and cached.risk_scores is not None:
            peer_list = None
            if cached.peer_comparison:
                peer_list = [PeerComparisonRow(**item) for item in cached.peer_comparison]

            w_high = float(cached.week52_high) if cached.week52_high else 0.0
            w_low = float(cached.week52_low) if cached.week52_low else 0.0
            c_price = float(cached.current_price) if cached.current_price else 0.0

            _, _, _, comment = calculate_valuation_band([w_high], [w_low], c_price)

            peer_target_per = peer_list[0].per if (peer_list and len(peer_list) > 0) else None
            peer_target_pbr = peer_list[0].pbr if (peer_list and len(peer_list) > 0) else None
            vol_score = cached.risk_scores.get("시장변동성") if isinstance(cached.risk_scores, dict) else None

            dynamic_reasons = build_comprehensive_reasons(
                opinion=cached.judgement,
                per=peer_target_per,
                pbr=peer_target_pbr,
                week52_high=w_high,
                week52_low=w_low,
                current_price=c_price,
                revenue_trend=cached.revenue_trend,
                volatility_score=vol_score,
            )

            return StockReport(
                stockCode=stock_code,
                reportDate=today_str,
                judgement=cached.judgement,
                judgementReasons=dynamic_reasons,
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

        # 5. 최신 뉴스 수집 (F-03-4): data_source 테이블에서 positive(긍정), negative(부정), neutral(중립) 최신순 1개씩 추출
        selected_rows = []
        used_ids = set()

        SENTIMENT_MAP = {
            "positive": "긍정",
            "negative": "부정",
            "neutral": "중립",
        }

        for target_sent in ["positive", "negative", "neutral"]:
            row = db.execute(
                text("""
                    SELECT id, headline, url, date, created_at, sentiment
                    FROM data_source
                    WHERE stock_id = :stock_id AND source_type = '뉴스' AND sentiment = :target_sent
                    ORDER BY date DESC, id DESC
                    LIMIT 1
                """),
                {"stock_id": stock_id, "target_sent": target_sent},
            ).fetchone()

            if row:
                selected_rows.append(row)
                used_ids.add(row.id)

        # 긍정/부정/중립 중 없는 라벨이 있다면 최신순으로 남은 자리 보충해서 3개 보장
        if len(selected_rows) < 3:
            fill_rows = db.execute(
                text("""
                    SELECT id, headline, url, date, created_at, sentiment
                    FROM data_source
                    WHERE stock_id = :stock_id AND source_type = '뉴스'
                    ORDER BY date DESC, id DESC
                    LIMIT 10
                """),
                {"stock_id": stock_id},
            ).fetchall()
            for r in fill_rows:
                if r.id not in used_ids:
                    selected_rows.append(r)
                    used_ids.add(r.id)
                    if len(selected_rows) == 3:
                        break

        latest_news = []
        now = datetime.now(timezone.utc)
        for row in selected_rows:
            diff_hours = max(1, int((now - row.created_at.replace(tzinfo=timezone.utc)).total_seconds() // 3600)) if row.created_at else 2
            raw_headline = sanitize_headline(str(row.headline or "").strip())
            clean_title = raw_headline.split("\n")[0][:75] + ("..." if len(raw_headline) > 75 else "")
            pub_name = extract_publisher(row.url)
            sent_label = SENTIMENT_MAP.get(str(row.sentiment).lower(), "중립")

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

        # 6. 뉴스 및 토스 커뮤니티 감성 통계 집계 (F-03-1 7대 스코어링 신호용)
        news_sent_rows = db.execute(
            text("""
                SELECT sentiment, COUNT(*) as cnt
                FROM data_source
                WHERE stock_id = :stock_id AND source_type = '뉴스'
                GROUP BY sentiment
            """),
            {"stock_id": stock_id},
        ).fetchall()
        news_sent_counts = {str(r.sentiment).lower(): int(r.cnt) for r in news_sent_rows if r.sentiment}

        comm_sent_rows = db.execute(
            text("""
                SELECT sentiment, COUNT(*) as cnt
                FROM data_source
                WHERE stock_id = :stock_id AND source_type = '토스_커뮤니티'
                GROUP BY sentiment
            """),
            {"stock_id": stock_id},
        ).fetchall()
        comm_sent_counts = {str(r.sentiment).lower(): int(r.cnt) for r in comm_sent_rows if r.sentiment}

        peer_rows = PEER_GROUPS.get(stock_code, [])
        target_peer = peer_rows[0] if peer_rows else None
        per_val = target_peer.per if target_peer else None
        pbr_val = target_peer.pbr if target_peer else None

        opinion, qual_signal, total_score = calculate_stock_opinion(
            news_sentiment_counts=news_sent_counts,
            community_sentiment_counts=comm_sent_counts,
            operating_margin=latest_opm,
            per=per_val,
            pbr=pbr_val,
            week52_high=week52_high,
            week52_low=week52_low,
            current_price=current_price,
            daily_candles=[{"close_price": float(r.close_price)} for r in candle_rows] if candle_rows else None,
        )

        stock_names = {"005930": "삼성전자", "000660": "SK하이닉스", "005380": "현대자동차", "373220": "LG에너지솔루션", "042660": "한화오션"}
        stock_name = stock_names.get(stock_code, stock_code)

        inv_summary = generate_investment_summary(
            stock_name=stock_name,
            current_price=current_price,
            opinion=opinion,
            qualitative_signal=qual_signal,
            news_items=[{"title": n.title} for n in latest_news] if latest_news else None,
            operating_margin=latest_opm,
        )


        # 60일 종가 기준 리스크 스코어 계산 (F-03-3)
        close_prices = [float(row.close_price) for row in reversed(candle_rows[:60])] if candle_rows else [current_price]
        risk_scores = calculate_risk_scores(close_prices, operating_profit_margin=latest_opm)

        rev_trend, profit_trend, margin_trend, growth_g, profit_g = "증가", "증가", "개선", "보통", "보통"
        if len(fin_rows) >= 2:
            rev_trend, profit_trend, margin_trend, growth_g, profit_g = analyze_financial_trends(
                float(fin_rows[1].revenue), float(fin_rows[0].revenue),
                float(fin_rows[1].operating_profit), float(fin_rows[0].operating_profit)
            )

        dynamic_reasons = build_comprehensive_reasons(
            opinion=opinion,
            per=per_val,
            pbr=pbr_val,
            week52_high=week52_high,
            week52_low=week52_low,
            current_price=current_price,
            operating_margin=latest_opm,
            revenue_trend=rev_trend,
            volatility_score=risk_scores.get("시장변동성"),
        )

        return StockReport(
            stockCode=stock_code,
            reportDate=today_str,
            judgement=opinion,
            qualitativeSignal=qual_signal,
            investmentSummary=inv_summary,
            judgementReasons=dynamic_reasons,
            revenueTrend=rev_trend,
            operatingProfitTrend=profit_trend,
            operatingMarginTrend=margin_trend,
            growthGrade=growth_g,
            profitabilityGrade=profit_g,
            financials=financials,
            latestNews=latest_news,
            riskScores=risk_scores,
            peerComparison=peer_rows,
            week52High=week52_high,
            week52Low=week52_low,
            currentPrice=current_price,
            valuationComment=valuation_comment,
        )



report_service = ReportService()
