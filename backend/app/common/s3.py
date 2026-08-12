"""ISSUE-E3: S3에 종목별로 미리 올려둔 긍정/부정 배경 영상을 조회한다.

네이밍 컨벤션: `{종목명}_positive.mp4` / `{종목명}_negative.mp4`
(예: 삼성전자_positive.mp4, 삼성전자_negative.mp4). 영상은 이 프로젝트가 만드는 게 아니라
사전에 누군가 S3에 올려두는 것이 전제라, 여기서는 "가져오는" 쪽만 담당한다.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

logger = logging.getLogger(__name__)

SENTIMENT_SUFFIX: dict[str, str] = {"긍정": "positive", "부정": "negative"}
PRESIGNED_URL_EXPIRE_SECONDS = 3600


def build_video_key(stock_name: str, sentiment: Literal["긍정", "부정"]) -> str:
    return f"{stock_name}_{SENTIMENT_SUFFIX[sentiment]}.mp4"


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
    """
    from botocore.exceptions import BotoCoreError, ClientError

    from app.core.config import settings

    if not settings.aws_s3_bucket:
        logger.info("AWS_S3_BUCKET 미설정 — 영상 조회 스킵")
        return None

    key = build_video_key(stock_name, sentiment)
    client = get_s3_client()

    try:
        client.head_object(Bucket=settings.aws_s3_bucket, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey"):
            logger.info("S3에 배경 영상 없음: %s", key)
        else:
            logger.warning("S3 head_object 실패(%s): %s", key, exc)
        return None
    except BotoCoreError as exc:
        logger.warning("S3 연결 실패, 영상 조회 스킵: %s", exc)
        return None

    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_s3_bucket, "Key": key},
            ExpiresIn=PRESIGNED_URL_EXPIRE_SECONDS,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("S3 presigned URL 생성 실패(%s): %s", key, exc)
        return None
