from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# ponytail: cwd로 ".env"를 찾으면 backend/에서 실행하냐 repo 루트에서 실행하냐에 따라
# 결과가 달라진다. 이 파일 기준 backend/.env로 고정해서 어디서 uvicorn을 띄우든 같게 만든다.
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    # --- infra ---
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sesac"
    redis_url: str = "redis://localhost:6379/0"

    # --- JWT (ISSUE-001) ---
    # ponytail: 필드명이 실제 .env의 ACCESS_TOKEN_EXPIRE_MINUTES/REFRESH_TOKEN_EXPIRE_DAYS와
    # 안 맞으면(예전엔 jwt_access_expire_minutes였음) pydantic-settings가 그 값을 조용히
    # 무시하고 기본값을 쓴다 — 여기 이름을 .env 쪽에 맞춰서 그 사고 재발을 막는다.
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    # --- 카카오 OAuth ---
    kakao_client_id: str = ""
    kakao_client_secret: str = ""
    kakao_redirect_uri: str = "http://localhost:8000/auth/kakao/callback"
    frontend_base_url: str = "http://localhost:3000"

    # --- F-01 한국투자증권 Open API ---
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    kis_websocket_url: str = "ws://ops.koreainvestment.com:21000"
    kis_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    kis_app_key: str = ""
    kis_app_secret: str = ""

    # --- F-03-2 DART 재무데이터 ---
    dart_api_key: str = ""

    # --- LLM (F-03/F-05 분류·요약) ---
    openai_api_key: str = ""

    # --- F-02 숏폼 배경 영상 저장 (ISSUE-E3) ---
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    aws_s3_bucket: str = ""
    aws_s3_endpoint_url: str | None = None  # 로컬 개발/테스트용 MinIO 등. 실 AWS면 비워둘 것

    # --- F-04, 보류 중이지만 재개 대비 자리만 유지 (PRODUCT.md ISSUE-E4) ---
    telegram_bot_token: str = ""

    # --- F-02 STT (ISSUE-E1, invest/ai/stt 이식) ---
    whisper_model_size: str = "base"  # ponytail: 원본은 small(~466MB). base(~145MB)가 로컬 CPU 데모엔 더 실용적, 정확도 필요하면 올리기
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = "ko"
    max_upload_size_mb: int = 200


settings = Settings()
