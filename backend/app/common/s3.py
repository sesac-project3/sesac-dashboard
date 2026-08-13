"""ISSUE-E3: S3에 종목별로 미리 올려둔 긍정/부정 배경 영상을 조회한다.

네이밍 컨벤션: `{종목명}_positive.mp4` / `{종목명}_negative.mp4`
(예: 삼성전자_positive.mp4, 삼성전자_negative.mp4). `{종목명}_긍정.mp4` / `{종목명}_부정.mp4`
같은 한글 접미사로 올라온 것도 있어 둘 다 시도한다. 영상은 이 프로젝트가 만드는 게 아니라
사전에 누군가 S3에 올려두는 것이 전제라, 여기서는 "가져오는" 쪽만 담당한다.
"""

from __future__ import annotations

import logging
import unicodedata
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)

# 문서화된 컨벤션은 영문 접미사(positive/negative)지만, 실제 업로드가 한글 접미사
# (긍정/부정)로 올라온 경우가 있어(예: LG에너지솔루션_긍정.mp4) 둘 다 시도한다.
SENTIMENT_SUFFIXES: dict[str, list[str]] = {"긍정": ["positive", "긍정"], "부정": ["negative", "부정"]}
PRESIGNED_URL_EXPIRE_SECONDS = 3600
# presigned URL은 서명에 만료시각이 박혀 있어서 매번 새로 발급하면 매번 다른 문자열이 된다.
# <video src>가 요청마다 바뀌면 브라우저가 "같은 영상"인 줄 모르고 HTTP 캐시를 못 써서
# 스크롤로 다시 돌아오거나 새로고침할 때마다 영상을 처음부터 다시 받는다.
# Redis에 URL 자체를 캐싱해서 이 기간 동안은 항상 같은 문자열을 돌려주고, 실제 만료(1시간)
# 전에 여유를 두고 갱신한다.
URL_CACHE_TTL_SECONDS = PRESIGNED_URL_EXPIRE_SECONDS - 300
NOT_FOUND_CACHE_TTL_SECONDS = 60  # 아직 안 올라온 영상은 짧게만 "없음"을 캐싱(계속 S3 두드리지 않게)


def build_video_keys(stock_name: str, sentiment: Literal["긍정", "부정"]) -> list[str]:
    return [f"{stock_name}_{suffix}.mp4" for suffix in SENTIMENT_SUFFIXES[sentiment]]


def _key_candidates(key: str) -> list[str]:
    """같은 한글이어도 NFC(완성형)/NFD(자모 분리) 두 가지 바이트 표현이 있을 수 있다.
    macOS Finder/일부 업로드 도구가 NFD로 저장해버려서 코드가 만든 NFC 키와 안 맞는
    경우가 실제로 있었음 — 두 형태를 다 시도해서 이 클래스의 버그를 원천 방지한다.
    """
    nfc = unicodedata.normalize("NFC", key)
    nfd = unicodedata.normalize("NFD", key)
    return [nfc] if nfc == nfd else [nfc, nfd]


@lru_cache(maxsize=1)
def get_s3_client():
    import boto3

    from app.core.config import settings

    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        endpoint_url=settings.aws_s3_endpoint_url or None,
    )


def get_shortform_video_url(stock_name: str, sentiment: Literal["긍정", "부정"]) -> str | None:
    """종목명+감성에 해당하는 배경 영상의 presigned URL을 반환한다.

    S3에 해당 키가 없거나 자격 증명/네트워크 문제가 있으면 예외를 던지지 않고 None을
    반환한다 — 배경 영상이 아직 준비 안 됐다고 숏폼 생성 자체가 막히면 안 되기 때문
    (PRD §8 가용성 요구사항과 같은 원칙: 없으면 없는 대로 자막 카드로 폴백).

    같은 (종목, 감성) 조합엔 URL_CACHE_TTL_SECONDS 동안 항상 같은 URL을 돌려준다 —
    브라우저가 <video src>를 같은 리소스로 인식해서 HTTP 캐시를 탈 수 있게 하기 위함.
    """
    from app.core.redis import redis_client

    cache_key = f"s3video:{stock_name}:{sentiment}"
    cached = redis_client.get(cache_key)
    if cached is not None:
        return cached or None  # 빈 문자열로 캐싱해둔 건 "없음"을 의미

    from botocore.exceptions import BotoCoreError, ClientError

    from app.core.config import settings

    if not settings.aws_s3_bucket:
        logger.info("AWS_S3_BUCKET 미설정 — 영상 조회 스킵")
        return None

    client = get_s3_client()
    found_key: str | None = None

    candidates = [
        candidate
        for base_key in build_video_keys(stock_name, sentiment)
        for candidate in _key_candidates(base_key)
    ]
    for key in candidates:
        try:
            client.head_object(Bucket=settings.aws_s3_bucket, Key=key)
            found_key = key
            break
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code not in ("404", "NoSuchKey"):
                logger.warning("S3 head_object 실패(%s): %s", key, exc)
                return None
        except BotoCoreError as exc:
            logger.warning("S3 연결 실패, 영상 조회 스킵: %s", exc)
            return None

    if found_key is None:
        logger.info("S3에 배경 영상 없음: %s (%s)", stock_name, sentiment)
        redis_client.set(cache_key, "", ex=NOT_FOUND_CACHE_TTL_SECONDS)
        return None

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_s3_bucket, "Key": found_key},
            ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("S3 presigned URL 생성 실패(%s): %s", found_key, exc)
        return None

    redis_client.set(cache_key, url, ex=URL_CACHE_TTL_SECONDS)
    return url
