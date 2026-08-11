from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.exceptions import BusinessException, business_exception_handler
from app.core.config import settings
from app.domain.auth.router import router as auth_router
from app.domain.community.router import router as community_router
from app.domain.news.router import router as news_router
from app.domain.reports.router import router as reports_router
from app.domain.shortforms.router import router as shortforms_router
from app.domain.stocks.router import router as stocks_router
from app.domain.stt.router import router as stt_router
from app.domain.telegram.router import router as telegram_router

app = FastAPI(title="sesac-dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(BusinessException, business_exception_handler)

for router in (
    auth_router,
    stocks_router,
    reports_router,
    news_router,
    shortforms_router,
    stt_router,
    telegram_router,
    community_router,
):
    app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
