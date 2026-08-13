"""홈 화면 대시보드: KIS 실데이터 기반 코스피/코스닥 지수+투자자동향, 5종목 랭킹."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.core.kis import kis_token_client
from app.domain.stocks.models import Stock
from app.domain.stocks.schemas import (
    HomeDashboard,
    InvestorTrend,
    MarketIndexDetail,
    RankingType,
    StockRankingItem,
)

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

# (indexType, 표시 타이틀, KIS 업종코드, KIS 시장구분 플래그)
_INDEX_DEFS: list[tuple[str, str, str, str]] = [
    ("KOSPI", "코스피", "0001", "KSP"),
    ("KOSDAQ", "코스닥", "1001", "KSQ"),
]


def _to_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _fetch_index_detail(index_type: str, title: str, index_code: str, market_flag: str) -> MarketIndexDetail | None:
    try:
        row = kis_token_client.market_investor_trend(index_code, market_flag)
    except BusinessException:
        logger.warning("KIS 지수/투자자동향 조회 실패: %s", title)
        return None
    if not row:
        return None

    change_percent = _to_float(row.get("bstp_nmix_prdy_ctrt"))
    return MarketIndexDetail(
        indexType=index_type,  # type: ignore[arg-type]
        title=title,
        value=_to_float(row.get("bstp_nmix_prpr")),
        change=_to_float(row.get("bstp_nmix_prdy_vrss")),
        changePercent=change_percent,
        isUp=change_percent >= 0,
        # KIS 순매수 대금은 백만원 단위로 온다 — 프론트 표기 단위(억원)에 맞춰 100으로 나눔.
        investors=InvestorTrend(
            personal=round(_to_float(row.get("prsn_ntby_tr_pbmn")) / 100, 0),
            foreign=round(_to_float(row.get("frgn_ntby_tr_pbmn")) / 100, 0),
            institution=round(_to_float(row.get("orgn_ntby_tr_pbmn")) / 100, 0),
        ),
    )


def fetch_stock_ranking_items(db: Session) -> list[StockRankingItem]:
    stocks = db.scalars(select(Stock).order_by(Stock.id)).all()
    items: list[StockRankingItem] = []
    for s in stocks:
        try:
            data = kis_token_client.current_price(s.code)
        except BusinessException:
            logger.warning("KIS 현재가 조회 실패: %s(%s)", s.name, s.code)
            continue
        if not data:
            continue
        change_percent = _to_float(data.get("prdy_ctrt"))
        items.append(
            StockRankingItem(
                code=s.code,
                name=s.name,
                price=_to_float(data.get("stck_prpr")),
                change=_to_float(data.get("prdy_vrss")),
                changePercent=change_percent,
                isUp=change_percent >= 0,
                volume=int(_to_float(data.get("acml_vol"))),
                # 종목 거래대금은 원 단위로 온다 -> 억원.
                tradingValue=round(_to_float(data.get("acml_tr_pbmn")) / 100_000_000, 1),
            )
        )
    return items


def _build_rankings(items: list[StockRankingItem]) -> dict[RankingType, list[StockRankingItem]]:
    return {
        "상승률": sorted(items, key=lambda x: x.changePercent, reverse=True),
        "하락률": sorted(items, key=lambda x: x.changePercent),
        "거래대금": sorted(items, key=lambda x: x.tradingValue, reverse=True),
        "거래량": sorted(items, key=lambda x: x.volume, reverse=True),
    }


def get_home_dashboard(db: Session) -> HomeDashboard:
    indices = [
        detail
        for detail in (_fetch_index_detail(*definition) for definition in _INDEX_DEFS)
        if detail is not None
    ]
    items = fetch_stock_ranking_items(db)
    return HomeDashboard(
        indices=indices,
        rankings=_build_rankings(items),
        asOf=datetime.now(KST),
    )
