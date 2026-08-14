import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.reports.schemas import PeerComparisonRow

logger = logging.getLogger(__name__)

# 수집 실패 시 폴백(Fallback) 데이터
PEER_FALLBACKS: Dict[str, List[PeerComparisonRow]] = {
    "005930": [
        PeerComparisonRow(name="삼성전자", per=18.27, pbr=1.87, roe=10.85, operating_margin=14.8),
        PeerComparisonRow(name="SK하이닉스", per=13.78, pbr=8.30, roe=44.15, operating_margin=52.0),
        PeerComparisonRow(name="DB하이텍", per=8.50, pbr=1.12, roe=13.50, operating_margin=18.2),
    ],
    "000660": [
        PeerComparisonRow(name="SK하이닉스", per=13.78, pbr=8.30, roe=44.15, operating_margin=52.0),
        PeerComparisonRow(name="삼성전자", per=18.27, pbr=1.87, roe=10.85, operating_margin=14.8),
        PeerComparisonRow(name="한미반도체", per=45.20, pbr=12.30, roe=27.20, operating_margin=35.1),
    ],
    "005380": [
        PeerComparisonRow(name="현대자동차", per=12.44, pbr=0.92, roe=8.41, operating_margin=7.4),
        PeerComparisonRow(name="기아", per=7.56, pbr=0.85, roe=12.92, operating_margin=11.2),
        PeerComparisonRow(name="KG모빌리티", per=6.20, pbr=0.65, roe=10.40, operating_margin=2.1),
    ],
    "373220": [
        PeerComparisonRow(name="LG에너지솔루션", per=-80.38, pbr=4.27, roe=-5.1, operating_margin=1.8),
        PeerComparisonRow(name="삼성SDI", per=-106.14, pbr=2.15, roe=-2.02, operating_margin=2.3),
        PeerComparisonRow(name="에코프로비엠", per=55.10, pbr=8.40, roe=15.20, operating_margin=5.8),
    ],
    "042660": [
        PeerComparisonRow(name="한화오션", per=18.90, pbr=4.24, roe=22.59, operating_margin=6.6),
        PeerComparisonRow(name="HD한국조선해양", per=10.36, pbr=1.92, roe=17.78, operating_margin=5.2),
        PeerComparisonRow(name="삼성중공업", per=35.77, pbr=4.64, roe=13.74, operating_margin=4.1),
    ],
}

# 피어 그룹 정의 (종목명, 티커)
PEER_CONFIG: Dict[str, List[tuple[str, str]]] = {
    "005930": [("삼성전자", "005930"), ("SK하이닉스", "000660"), ("DB하이텍", "000990")],
    "000660": [("SK하이닉스", "000660"), ("삼성전자", "005930"), ("한미반도체", "042700")],
    "005380": [("현대자동차", "005380"), ("기아", "000270"), ("KG모빌리티", "003620")],
    "373220": [("LG에너지솔루션", "373220"), ("삼성SDI", "006400"), ("에코프로비엠", "247540")],
    "042660": [("한화오션", "042660"), ("HD한국조선해양", "009540"), ("삼성중공업", "010140")],
}



def check_krx_credentials() -> None:
    """
    KRX_ID, KRX_PW 환경변수 검증
    """
    krx_id = os.getenv("KRX_ID")
    krx_pw = os.getenv("KRX_PW")
    if not krx_id or not krx_pw:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            krx_id = os.getenv("KRX_ID")
            krx_pw = os.getenv("KRX_PW")
        except Exception:
            pass

    if not krx_id or not krx_pw:
        raise ValueError("KRX 로그인 정보가 없습니다. .env에 KRX_ID, KRX_PW를 설정해주세요")



def calculate_roe(eps: Optional[float], bps: Optional[float]) -> Optional[float]:
    """
    ROE(%) = (EPS / BPS) * 100 공식으로 ROE 계산.
    BPS가 0이거나 조회 실패 시 None 반환.
    """
    if eps is None or bps is None or bps == 0:
        return None
    try:
        roe = (eps / bps) * 100
        return round(roe, 2)
    except Exception:
        return None


def fetch_krx_fundamental(ticker: str, date_str: Optional[str] = None) -> Dict[str, Optional[float]]:
    """
    pykrx.stock.get_market_fundamental()를 사용하여 PER, PBR, EPS, BPS 수집 및 ROE 계산.
    """
    check_krx_credentials()

    from pykrx import stock

    if not date_str:
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")

    df = None
    target_dt = datetime.strptime(date_str, "%Y%m%d") if len(date_str) == 8 else datetime.now()
    
    for i in range(5):
        search_date = (target_dt - timedelta(days=i)).strftime("%Y%m%d")
        try:
            temp_df = stock.get_market_fundamental(search_date, search_date, ticker)
            if temp_df is not None and not temp_df.empty:
                df = temp_df
                break
        except Exception as e:
            logger.warning(f"[pykrx] {search_date} {ticker} 조회 실패: {e}")
            continue

    if df is None or df.empty:
        return {"per": None, "pbr": None, "eps": None, "bps": None, "roe": None}

    row = df.iloc[0]
    per = float(row["PER"]) if "PER" in row and row["PER"] != 0 else None
    pbr = float(row["PBR"]) if "PBR" in row and row["PBR"] != 0 else None
    eps = float(row["EPS"]) if "EPS" in row and row["EPS"] != 0 else None
    bps = float(row["BPS"]) if "BPS" in row and row["BPS"] != 0 else None
    roe = calculate_roe(eps, bps)

    return {"per": per, "pbr": pbr, "eps": eps, "bps": bps, "roe": roe}


def fetch_opm_from_db(db: Session, stock_code: str) -> Optional[float]:
    """
    financial_statements DB 테이블에서 매출액 및 영업이익을 가져와 영업이익률(%) 계산.
    """
    try:
        row = db.execute(
            text("""
                SELECT fs.revenue, fs.operating_profit, fs.operating_margin
                FROM financial_statements fs
                JOIN stocks s ON s.id = fs.stock_id
                WHERE s.code = :code
                ORDER BY fs.fiscal_year DESC
                LIMIT 1
            """),
            {"code": stock_code},
        ).fetchone()

        if not row:
            return None

        if row.operating_margin is not None:
            return float(row.operating_margin)

        revenue = float(row.revenue) if row.revenue else 0.0
        operating_profit = float(row.operating_profit) if row.operating_profit else 0.0

        if revenue > 0:
            return round((operating_profit / revenue) * 100, 2)
        return None
    except Exception as e:
        logger.error(f"[DB OPM Fetch Error] {stock_code}: {e}")
        return None


def get_peer_comparison_data(db: Session, stock_code: str) -> List[PeerComparisonRow]:
    """
    종목 코드에 해당하는 동종업계 비교 데이터 수집 (pykrx + DB + Fallback 조합)
    """
    peers = PEER_CONFIG.get(stock_code, [])
    fallbacks = PEER_FALLBACKS.get(stock_code, [])
    fallback_map = {f.name: f for f in fallbacks}

    result: List[PeerComparisonRow] = []

    for name, ticker in peers:
        if not ticker.isdigit():
            fb = fallback_map.get(name)
            if fb:
                result.append(fb)
            else:
                result.append(PeerComparisonRow(name=name, per=None, pbr=None, roe=None, operating_margin=None))
            continue

        try:
            fund = fetch_krx_fundamental(ticker)
            opm = fetch_opm_from_db(db, ticker)

            fb = fallback_map.get(name)
            result.append(
                PeerComparisonRow(
                    name=name,
                    per=fund.get("per") if fund.get("per") is not None else (fb.per if fb else None),
                    pbr=fund.get("pbr") if fund.get("pbr") is not None else (fb.pbr if fb else None),
                    roe=fund.get("roe") if fund.get("roe") is not None else (fb.roe if fb else None),
                    operating_margin=opm if opm is not None else (fb.operating_margin if fb else None),
                )
            )
        except Exception as e:
            logger.error(f"[Peer Comparison Error] {name} ({ticker}): {e}")
            fb = fallback_map.get(name)
            if fb:
                result.append(fb)
            else:
                result.append(PeerComparisonRow(name=name, per=None, pbr=None, roe=None, operating_margin=None))

    return result
