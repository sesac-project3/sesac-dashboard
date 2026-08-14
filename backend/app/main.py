import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.exceptions import BusinessException, business_exception_handler
from app.core.config import settings

# 루트 로거 레벨 기본값(WARNING)을 그대로 두면 logger.info(...)가 전부 조용히 버려진다 —
# app/core/kis.py의 "[KIS] New access token issued." 같은 개발용 안내 로그를 포함해서,
# 지금까지 이 앱의 어떤 info 로그도 실제로 출력된 적이 없었다. INFO까지는 보이게 설정.
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
from app.domain.auth.router import router as auth_router
from app.domain.community.router import router as community_router
from app.domain.news.router import router as news_router
from app.domain.reports.router import router as reports_router
from app.domain.shortforms.router import router as shortforms_router
from app.domain.stocks.router import router as stocks_router
from app.domain.stocks.market_subscription import restore_kis_subscriptions, subscribe_candle_events
from app.domain.stt.router import router as stt_router
from app.domain.telegram.router import router as telegram_router
from app.domain.telegram.polling import run_telegram_polling
from app.domain.telegram.scheduler import run_telegram_scheduler
from app.domain.watchlists.router import router as watchlists_router

@asynccontextmanager
async def lifespan(_: FastAPI):
    stop_event = asyncio.Event()
    subscriber_task = asyncio.create_task(subscribe_candle_events(stop_event))
    telegram_polling_task = asyncio.create_task(run_telegram_polling(stop_event))
    telegram_scheduler_task = asyncio.create_task(run_telegram_scheduler(stop_event))
    await restore_kis_subscriptions()
    try:
        yield
    finally:
        stop_event.set()
        await subscriber_task
        await telegram_polling_task
        await telegram_scheduler_task


app = FastAPI(title="sesac-dashboard API", lifespan=lifespan)

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
    watchlists_router,
):
    app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
