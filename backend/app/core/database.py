from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


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
