from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILES = [
    _BACKEND_DIR / ".env",
    _BACKEND_DIR.parent / ".env",
]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, extra="ignore")

    # --- infra ---
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sesac"
    redis_url: str = "redis://localhost:6379/0"

    # --- 환경 구분 ---
    # 로컬 docker-compose(각자 컨테이너, Redis도 개발자별)로 띄우면 기본값(development) 그대로.
    # 배포 환경에서는 반드시 APP_ENV=production으로 설정 — KIS 인증값을 .env가 아니라
    # Redis에서 관리하게 갈라진다 (app/core/kis.py 참고).
    app_env: str = "development"

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
    # 개발 환경 전용 — 서버가 새로 발급하면 로그에 아래 형식으로 출력된다. 그대로 .env에
    # 복사해두면 다음 서버 재시작부터 재발급 없이 재사용된다(dev는 Redis를 인증 공유
    # 용도로 안 쓰기 때문). 배포 환경(APP_ENV=production)에서는 이 값 대신 Redis
    # (kis:access_token 등)를 쓰므로 여기 채워둬도 무시된다.
    kis_access_token: str = ""
    kis_access_token_expires_at: str = ""
    kis_ws_approval_key: str = ""
    kis_ws_approval_key_expires_at: str = ""

    # --- F-03-2 DART 재무데이터 ---
    dart_api_key: str = ""

    # --- LLM (F-03/F-05 분류·요약) ---
    openai_api_key: str = ""

    # --- 네이버 Open API (뉴스 검색) ---
    naver_client_id: str = ""
    naver_secret_key: str = ""
    naver_client_secret: str = ""

    # --- F-02 숏폼 배경 영상 저장 (ISSUE-E3) ---
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-northeast-2"
    aws_s3_bucket: str = ""
    aws_s3_endpoint_url: str | None = None  # 로컬 개발/테스트용 MinIO 등. 실 AWS면 비워둘 것

    # --- F-04, 보류 중이지만 재개 대비 자리만 유지 (PRODUCT.md ISSUE-E4) ---
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    # --- F-02 STT (ISSUE-E1, invest/ai/stt 이식) ---
    whisper_model_size: str = "base"  # ponytail: 원본은 small(~466MB). base(~145MB)가 로컬 CPU 데모엔 더 실용적, 정확도 필요하면 올리기
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = "ko"
    max_upload_size_mb: int = 200

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"


settings = Settings()
