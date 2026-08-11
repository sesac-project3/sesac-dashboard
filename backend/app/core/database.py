from datetime import datetime

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """모든 테이블에 있는 created_at/updated_at 공통 선언.

    server_default가 없으면 SQLAlchemy가 INSERT에 NULL을 명시적으로 실어 보내서
    DB의 `DEFAULT now()`를 못 타고 NOT NULL 위반이 난다 — 각 모델에서 따로 값을
    채워주는 대신 여기 한 곳에서 고쳐서 모든 모델이 자동으로 혜택을 받게 한다.
    updated_at 갱신은 DB 트리거(set_updated_at)가 담당하므로 onupdate는 선언하지 않는다.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # 실행: cd backend && .venv/bin/python -m app.core.database
    from sqlalchemy import text

    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
    print(f"DB 연결 확인 완료: {engine.url.host}:{engine.url.port}/{engine.url.database}")
