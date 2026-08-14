"""홈 화면 대시보드: KIS 실데이터 기반 코스피/코스닥 지수+투자자동향, 5종목 랭킹.

지수/랭킹 조회 결과는 Redis에 짧게(수 초) 캐싱한다 — 홈 대시보드가 5초마다 자동
갱신을 도는데, 여러 사용자가 동시에 보고 있거나 관심종목 페이지가 같은 데이터를
또 필요로 할 때마다 매번 KIS를 새로 부르면 느리고(각 종목당 왕복 1회씩) KIS 자체
호출 한도(초당 20건, 앱키 전체 사용자 공유)도 금방 소모된다. 캐시 TTL은 자동 갱신
주기보다 살짝 짧게 잡아서, 매 폴링 사이클마다는 대체로 새 값을 받아온다.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.naver_news import fetch_naver_news_for_stock
from app.common.openai_client import get_openai_client
from app.core.kis import kis_token_client
from app.core.redis import redis_client
from app.domain.stocks.models import Stock
from app.domain.stocks.schemas import (
    HomeDashboard,
    InvestorTrend,
    MarketIndexDetail,
    MarketIssue,
    RankingType,
    StockRankingItem,
)

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

CACHE_TTL_SECONDS = 4  # 홈 대시보드 자동 갱신 주기(5초)보다 살짝 짧게
_RANKING_CACHE_KEY = "market:ranking-items"
_INDEX_CACHE_KEY = "market:index-details"

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


def _fetch_index_details_live() -> list[MarketIndexDetail]:
    return [
        detail
        for detail in (_fetch_index_detail(*definition) for definition in _INDEX_DEFS)
        if detail is not None
    ]


def fetch_index_details() -> list[MarketIndexDetail]:
    cached = redis_client.get(_INDEX_CACHE_KEY)
    if cached:
        return [MarketIndexDetail.model_validate(d) for d in json.loads(cached)]

    indices = _fetch_index_details_live()
    if indices:  # KIS가 통째로 실패해서 비었으면 캐싱하지 않는다 — 다음 요청이 바로 재시도
        redis_client.set(
            _INDEX_CACHE_KEY,
            json.dumps([idx.model_dump(mode="json") for idx in indices]),
            ex=CACHE_TTL_SECONDS,
        )
    return indices


def _fetch_stock_ranking_items_live(db: Session) -> list[StockRankingItem]:
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


def fetch_stock_ranking_items(db: Session) -> list[StockRankingItem]:
    cached = redis_client.get(_RANKING_CACHE_KEY)
    if cached:
        return [StockRankingItem.model_validate(d) for d in json.loads(cached)]

    items = _fetch_stock_ranking_items_live(db)
    if items:
        redis_client.set(
            _RANKING_CACHE_KEY,
            json.dumps([item.model_dump(mode="json") for item in items]),
            ex=CACHE_TTL_SECONDS,
        )
    return items


def _build_rankings(items: list[StockRankingItem]) -> dict[RankingType, list[StockRankingItem]]:
    return {
        "상승률": sorted(items, key=lambda x: x.changePercent, reverse=True),
        "하락률": sorted(items, key=lambda x: x.changePercent),
        "거래대금": sorted(items, key=lambda x: x.tradingValue, reverse=True),
        "거래량": sorted(items, key=lambda x: x.volume, reverse=True),
    }


_MARKET_ISSUE_BUCKET_MINUTES = 15  # 0/15/30/45분 단위로만 갱신 — 화면 하단 "갱신 시간"도 이 경계에 맞춘다


def _current_market_issue_bucket(now: datetime) -> datetime:
    floored_minute = (now.minute // _MARKET_ISSUE_BUCKET_MINUTES) * _MARKET_ISSUE_BUCKET_MINUTES
    return now.replace(minute=floored_minute, second=0, microsecond=0)


def _market_issue_cache_key(bucket: datetime) -> str:
    return f"market:ai-issue:{bucket.strftime('%Y%m%d%H%M')}"


def _fetch_market_headlines() -> list[str]:
    """네이버 뉴스 검색 API로 '코스피'/'코스닥' 각각 최신 3건(현재 시점 기준)을 가져온다.
    종목 리포트(report_service)와 같은 fetch_naver_news_for_stock을 재사용 — 그 함수는
    아무 검색어나 받아 제목에 해당 문자열이 포함된 기사를 걸러주므로 지수명 검색에도 그대로 쓸 수 있다."""
    headlines: list[str] = []
    for query in ("코스피", "코스닥"):
        for item in fetch_naver_news_for_stock(query, limit=3):
            headlines.append(item["title"])
    return headlines


def _generate_market_issue(indices: list[MarketIndexDetail]) -> MarketIssue | None:
    """[KIS 지수 실데이터] + [코스피/코스닥 검색 네이버 뉴스 최신 6건]에 있는 사실만으로
    '국내 주요 이슈' 카드 문구를 만든다. 근거가 하나도 없으면(지수 조회 실패) 지어내지 않고 None."""
    if not indices:
        return None
    client = get_openai_client()
    if client is None:
        return None

    headlines = _fetch_market_headlines()
    index_facts = [
        f"{idx.title}: {idx.value:,.2f} ({'+' if idx.change >= 0 else ''}{idx.change:,.2f}, "
        f"{'+' if idx.changePercent >= 0 else ''}{idx.changePercent:.2f}%), "
        f"개인 {idx.investors.personal:,.0f}억/외국인 {idx.investors.foreign:,.0f}억/"
        f"기관 {idx.investors.institution:,.0f}억 순매수"
        for idx in indices
    ]

    system = (
        "너는 증권 앱 홈 화면에 들어가는 '국내 주요 이슈' 카드를 쓰는 애널리스트야. "
        "아래 [지수 데이터]와 [코스피/코스닥 뉴스 헤드라인]에 없는 수치·사건은 절대 지어내지 마. "
        "뉴스가 비어 있으면 지수 데이터(등락률/수급)만으로 서술하고 원인을 추측하지 마.\n"
        "반드시 이 형식으로 출력해:\n"
        "1번째 줄: 12자 내외의 제목만\n"
        "2번째 줄부터: 코스피/코스닥 등락과 수급, 뉴스에 실제로 언급된 이슈를 묶어 2~3문장, "
        "합쳐서 120자 내외. 한자(漢字)는 절대 섞지 마."
    )
    user = (
        "[지수 데이터]\n" + "\n".join(index_facts) + "\n\n[코스피/코스닥 뉴스 헤드라인]\n"
        + ("\n".join(f"- {h}" for h in headlines) if headlines else "(현재 검색된 뉴스 없음)")
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=300,
        )
        lines = [ln.strip() for ln in (response.choices[0].message.content or "").splitlines() if ln.strip()]
        if len(lines) < 2:
            return None
        title = re.sub(r"^[-*•]\s*", "", lines[0]).strip()
        body = " ".join(re.sub(r"^[-*•]\s*", "", ln).strip() for ln in lines[1:])
        return MarketIssue(title=title, text=body, updatedAt=_current_market_issue_bucket(datetime.now(KST)))
    except Exception:
        logger.exception("국내 주요 이슈 LLM 생성 실패")
        return None


def get_market_issue() -> MarketIssue | None:
    now = datetime.now(KST)
    bucket = _current_market_issue_bucket(now)
    cache_key = _market_issue_cache_key(bucket)

    cached = redis_client.get(cache_key)
    if cached is not None:
        return MarketIssue.model_validate(json.loads(cached)) if cached else None

    issue = _generate_market_issue(fetch_index_details())
    # 다음 15분 경계까지만 캐시 유지 — 경계를 넘어가면 자연히 새 버킷 키로 다시 생성된다.
    next_bucket = bucket + timedelta(minutes=_MARKET_ISSUE_BUCKET_MINUTES)
    ttl = max(1, int((next_bucket - now).total_seconds()))
    # 실패도 빈 문자열로 캐싱해서, 같은 버킷 안에서는 LLM을 반복 호출하지 않는다.
    redis_client.set(cache_key, json.dumps(issue.model_dump(mode="json")) if issue else "", ex=ttl)
    return issue


def get_home_dashboard(db: Session) -> HomeDashboard:
    indices = fetch_index_details()
    items = fetch_stock_ranking_items(db)
    return HomeDashboard(
        indices=indices,
        rankings=_build_rankings(items),
        asOf=datetime.now(KST),
    )
