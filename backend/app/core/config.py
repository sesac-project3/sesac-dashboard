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
    jwt_secret_key: str = "change-me"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 14

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

    # --- F-02 숏폼 배경 영상 저장 ---
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    aws_s3_bucket: str = ""

    # --- F-04, 보류 중이지만 재개 대비 자리만 유지 (PRODUCT.md ISSUE-E4) ---
    telegram_bot_token: str = ""


settings = Settings()
