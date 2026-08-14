import html
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from app.core.config import settings


def clean_html_tags(text: str) -> str:
    """네이버 뉴스 검색 결과 제목/요약에서 HTML 태그 및 HTML 엔티티 제거"""
    if not text:
        return ""
    # HTML 엔티티 해제 (&quot;, &amp;, &lt;, &gt; 등)
    unescaped = html.unescape(text)
    # <b>...</b> 등 HTML 태그 정규식 제거
    cleaned = re.sub(r"<[^>]+>", "", unescaped)
    return cleaned.strip()


def parse_pub_date(pub_date_str: str) -> str:
    """RFC 822 날짜 포맷 (Wed, 13 Aug 2026 15:30:00 +0900)을 YYYY-MM-DD 포맷으로 변환"""
    if not pub_date_str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return pub_date_str[:10] if len(pub_date_str) >= 10 else pub_date_str


def evaluate_sentiment(title: str) -> str:
    """기사 제목 기반 단순 키워드 감성 분석 ('긍정' | '부정' | '중립')"""
    positive_keywords = ["상승", "급등", "호조", "최고", "돌풍", "수주", "흑자", "성장", "회복", "호실적", "급증", "호재", "강세", "수혜"]
    negative_keywords = ["하락", "급락", "우려", "둔화", "적자", "폭락", "감소", "위기", "악재", "부진", "손실", "비상", "약세"]

    pos_count = sum(1 for kw in positive_keywords if kw in title)
    neg_count = sum(1 for kw in negative_keywords if kw in title)

    if pos_count > neg_count:
        return "긍정"
    elif neg_count > pos_count:
        return "부정"
    return "중립"


def _request_naver_api(url: str, headers: dict) -> list[dict]:
    """네이버 API HTTP 요청 및 JSON 파싱 공통 헬퍼"""
    req = urllib.request.Request(url)
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return []
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return data.get("items", [])
    except Exception:
        return []


def fetch_naver_news_for_stock(stock_name: str, limit: int = 3) -> list[dict]:
    """
    네이버 뉴스 검색 API (NCP Gateway 및 Developers Gateway 모두 지원) 호출하여
    제목(헤드라인)에 해당 stock_name이 정확히 포함된 최신 뉴스 top 3 반환
    """
    client_id = settings.naver_client_id
    client_secret = settings.naver_secret_key or settings.naver_client_secret

    if not client_id or not client_secret:
        return []

    encoded_query = urllib.parse.quote(stock_name)
    items = []

    # 1. 네이버 클라우드 플랫폼 (NCP NAVER API HUB) 게이트웨이 시도
    ncp_url = f"https://naverapihub.apigw.ntruss.com/search/v1/news?query={encoded_query}&display=15&sort=date"
    ncp_headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret,
    }
    items = _request_naver_api(ncp_url, ncp_headers)

    # 2. NCP 실패 시 기존 Developers Open API 게이트웨이 시도
    if not items:
        dev_url = f"https://openapi.naver.com/v1/search/news.json?query={encoded_query}&display=15&sort=date"
        dev_headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        items = _request_naver_api(dev_url, dev_headers)

    if not items:
        return []

    filtered_news = []
    for idx, item in enumerate(items, 1):
        raw_title = item.get("title", "")
        clean_title = clean_html_tags(raw_title)

        # 헤드라인(제목)에 종목명이 포함된 기사만 필터링
        if stock_name not in clean_title:
            continue

        pub_date = parse_pub_date(item.get("pubDate", ""))
        sentiment = evaluate_sentiment(clean_title)
        link = item.get("originallink") or item.get("link") or "#"

        filtered_news.append({
            "id": f"naver_{idx}_{abs(hash(clean_title))}",
            "title": clean_title,
            "publisher": "네이버 뉴스",
            "publishedAt": pub_date,
            "url": link,
            "sentiment": sentiment,
        })

        if len(filtered_news) >= limit:
            break

    # 만약 제목에 종목명이 포함된 기사가 limit개 미만이면 검색 상위 기사로 보충
    if len(filtered_news) < limit:
        for idx, item in enumerate(items, 1):
            clean_title = clean_html_tags(item.get("title", ""))
            link = item.get("originallink") or item.get("link") or "#"
            if any(n["title"] == clean_title for n in filtered_news):
                continue

            pub_date = parse_pub_date(item.get("pubDate", ""))
            sentiment = evaluate_sentiment(clean_title)

            filtered_news.append({
                "id": f"naver_fallback_{idx}",
                "title": clean_title,
                "publisher": "네이버 뉴스",
                "publishedAt": pub_date,
                "url": link,
                "sentiment": sentiment,
            })

            if len(filtered_news) >= limit:
                break

    return filtered_news[:limit]
