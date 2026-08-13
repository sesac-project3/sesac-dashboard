import asyncio
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.auth.models import User
from app.domain.stocks.models import Stock
from app.domain.watchlists.models import Watchlist
from app.domain.stocks.home_dashboard_service import fetch_index_details, fetch_stock_ranking_items
from app.domain.telegram.models import TelegramNotification
from app.domain.telegram.router import send_telegram_message

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

async def send_morning_briefing(db: Session):
    logger.info("[Telegram Scheduler] Dispatching Morning Briefing (08:00)...")
    today_date = date.today()
    
    # Fetch index details (KOSPI/KOSDAQ)
    indices = fetch_index_details()
    kospi_text = "N/A"
    kosdaq_text = "N/A"
    for idx in indices:
        if idx.indexType == "KOSPI":
            kospi_text = f"{idx.value:,.2f} ({'+' if idx.isUp else ''}{idx.changePercent:.2f}%)"
        elif idx.indexType == "KOSDAQ":
            kosdaq_text = f"{idx.value:,.2f} ({'+' if idx.isUp else ''}{idx.changePercent:.2f}%)"

    # Find all users linked to Telegram
    users = db.scalars(select(User).where(User.telegram_chat_id != None)).all()
    for user in users:
        # Check if already sent
        existing = db.scalar(
            select(TelegramNotification).where(
                TelegramNotification.user_id == user.id,
                TelegramNotification.notification_type == "MORNING_BRIEFING",
                TelegramNotification.sent_date == today_date
            )
        )
        if existing:
            continue

        # Get user's watchlist
        watchlist_stocks = db.scalars(
            select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user.id)
        ).all()

        watchlist_text = ""
        if watchlist_stocks:
            watchlist_text = "<b>2. 관심종목 전일 마감 현황</b>\n"
            for stock in watchlist_stocks:
                watchlist_text += f"• <b>{stock.name}({stock.code})</b>: 전일 대비 리포트 및 지수 대조 경보 준비 완료.\n"
        else:
            watchlist_text = "<b>2. 관심종목 정보</b>\n등록된 관심종목이 없습니다. 웹 대시보드에서 관심종목을 등록하시면 분석 알림을 받으실 수 있습니다.\n"

        briefing_text = (
            f"🌤️ <b>[오전 시장 브리핑] {today_date.strftime('%Y년 %m월 %d일')}</b>\n\n"
            f"<b>1. 주요 지수 마감 정보</b>\n"
            f"• 코스피: {kospi_text}\n"
            f"• 코스닥: {kosdaq_text}\n\n"
            f"{watchlist_text}\n"
            f"<b>3. 오늘의 투자 관전 포인트</b>\n"
            f"• 어제 장 마감 동향과 글로벌 거시 지표에 기반해 오늘 장 개장 시 변동성이 있을 수 있으니 관심종목 실시간 캔들을 예의주시하세요.\n\n"
            f"👉 <a href=\"{settings.frontend_base_url}\">대시보드로 이동하기</a>\n\n"
            f"오늘도 성공적인 투자 하루 되세요! 👍"
        )

        try:
            await send_telegram_message(user.telegram_chat_id, briefing_text)
            # Log dispatch to prevent duplicate sends
            log_entry = TelegramNotification(
                user_id=user.id,
                notification_type="MORNING_BRIEFING",
                sent_date=today_date
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"[Telegram Scheduler] Failed to send morning briefing to user {user.id}: {e}")
            db.rollback()

async def send_evening_briefing(db: Session):
    logger.info("[Telegram Scheduler] Dispatching Evening Briefing (16:30)...")
    today_date = date.today()
    
    indices = fetch_index_details()
    kospi_text = "N/A"
    kosdaq_text = "N/A"
    for idx in indices:
        if idx.indexType == "KOSPI":
            kospi_text = f"{idx.value:,.2f} ({'+' if idx.isUp else ''}{idx.changePercent:.2f}%)"
        elif idx.indexType == "KOSDAQ":
            kosdaq_text = f"{idx.value:,.2f} ({'+' if idx.isUp else ''}{idx.changePercent:.2f}%)"

    stock_items = fetch_stock_ranking_items(db)
    price_by_code = {item.code: item for item in stock_items}

    users = db.scalars(select(User).where(User.telegram_chat_id != None)).all()
    for user in users:
        existing = db.scalar(
            select(TelegramNotification).where(
                TelegramNotification.user_id == user.id,
                TelegramNotification.notification_type == "AFTERNOON_BRIEFING",
                TelegramNotification.sent_date == today_date
            )
        )
        if existing:
            continue

        watchlist_stocks = db.scalars(
            select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user.id)
        ).all()

        watchlist_text = ""
        if watchlist_stocks:
            watchlist_text = "<b>2. 관심종목 당일 등락 요약</b>\n"
            for stock in watchlist_stocks:
                item = price_by_code.get(stock.code)
                if item:
                    sign = "+" if item.changePercent >= 0 else ""
                    watchlist_text += (
                        f"• <b>{stock.name}({stock.code})</b>: "
                        f"{item.price:,.0f}원 ({sign}{item.changePercent:.2f}%) "
                        f"[<a href=\"{settings.frontend_base_url}/stock/{stock.code}\">AI 리포트 딥링크</a>]\n"
                    )
                else:
                    watchlist_text += f"• <b>{stock.name}({stock.code})</b>: 가격 정보 없음\n"
        else:
            watchlist_text = "<b>2. 관심종목 정보</b>\n등록된 관심종목이 없습니다.\n"

        briefing_text = (
            f"🔔 <b>[장 마감 브리핑] {today_date.strftime('%Y년 %m월 %d일')}</b>\n\n"
            f"오늘 국내 증시 및 관심종목 마감 결과입니다.\n\n"
            f"<b>1. 시장 지수 마감</b>\n"
            f"• 코스피: {kospi_text}\n"
            f"• 코스닥: {kosdaq_text}\n\n"
            f"{watchlist_text}\n"
            f"상세 분석 내용 및 관련 핵심 뉴스는 AI 리포트 딥링크로 접속해 확인해 주세요."
        )

        try:
            await send_telegram_message(user.telegram_chat_id, briefing_text)
            log_entry = TelegramNotification(
                user_id=user.id,
                notification_type="AFTERNOON_BRIEFING",
                sent_date=today_date
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"[Telegram Scheduler] Failed to send evening briefing to user {user.id}: {e}")
            db.rollback()

async def check_price_alerts(db: Session):
    logger.info("[Telegram Scheduler] Checking price alerts...")
    today_date = date.today()

    indices = fetch_index_details()
    index_change_by_market = {"KOSPI": 0.0, "KOSDAQ": 0.0}
    for idx in indices:
        index_change_by_market[idx.indexType] = idx.changePercent

    stock_items = fetch_stock_ranking_items(db)
    price_by_code = {item.code: item for item in stock_items}

    users = db.scalars(select(User).where(User.telegram_chat_id != None)).all()
    for user in users:
        watchlist_stocks = db.scalars(
            select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user.id)
        ).all()

        for stock in watchlist_stocks:
            item = price_by_code.get(stock.code)
            if not item:
                continue

            # Check relative change vs market index
            market_type = "KOSDAQ" if stock.market == "KOSDAQ" else "KOSPI"
            index_change = index_change_by_market.get(market_type, 0.0)
            relative_change = item.changePercent - index_change

            # Threshold: Relative change exceeds ±3%p OR absolute change exceeds ±5%
            exceeds_relative = abs(relative_change) >= 3.0
            exceeds_absolute = abs(item.changePercent) >= 5.0

            if exceeds_relative or exceeds_absolute:
                # Check if already alert sent today for this stock to this user
                existing = db.scalar(
                    select(TelegramNotification).where(
                        TelegramNotification.user_id == user.id,
                        TelegramNotification.notification_type == "PRICE_ALERT",
                        TelegramNotification.stock_id == stock.id,
                        TelegramNotification.sent_date == today_date
                    )
                )
                if existing:
                    continue

                sign = "+" if item.changePercent >= 0 else ""
                diff_sign = "+" if relative_change >= 0 else ""
                
                alert_text = (
                    f"🚨 <b>[지수대비 급변동 경보]</b>\n\n"
                    f"관심종목 <b>{stock.name}({stock.code})</b>가 지수 대비 큰 변동을 기록하고 있습니다!\n\n"
                    f"• 현재가: {item.price:,.0f}원\n"
                    f"• 당일 등락률: {sign}{item.changePercent:.2f}%\n"
                    f"• {market_type} 지수대비: {diff_sign}{relative_change:.2f}%p {'아웃퍼폼!' if relative_change >= 0 else '언더퍼폼'}\n\n"
                    f"👉 <a href=\"{settings.frontend_base_url}/stock/{stock.code}\">종목 심층 AI 분석 보기</a>"
                )

                try:
                    await send_telegram_message(user.telegram_chat_id, alert_text)
                    log_entry = TelegramNotification(
                        user_id=user.id,
                        notification_type="PRICE_ALERT",
                        stock_id=stock.id,
                        sent_date=today_date
                    )
                    db.add(log_entry)
                    db.commit()
                except Exception as e:
                    logger.error(f"[Telegram Scheduler] Failed to send price alert for user {user.id}, stock {stock.code}: {e}")
                    db.rollback()

async def run_telegram_scheduler(stop_event: asyncio.Event):
    logger.info("[Telegram Scheduler] Starting Telegram notification scheduler...")
    
    while not stop_event.is_set():
        now = datetime.now(KST)
        current_time = now.time()
        
        # We need a new DB session for each schedule run
        db = SessionLocal()
        try:
            # 1. Morning Briefing Trigger (08:00 KST)
            # Checked in time window 08:00:00 - 08:01:00
            if current_time.hour == 8 and current_time.minute == 0:
                await send_morning_briefing(db)
                
            # 2. Evening Briefing Trigger (16:30 KST)
            # Checked in time window 16:30:00 - 16:31:00
            elif current_time.hour == 16 and current_time.minute == 30:
                await send_evening_briefing(db)
                
            # 3. Price Spike Alerts Check (Monday - Friday, 09:00 - 15:30 KST)
            # Checked every 1 minute during market hours
            elif now.weekday() < 5 and (
                (current_time.hour == 9 and current_time.minute >= 0) or
                (9 < current_time.hour < 15) or
                (current_time.hour == 15 and current_time.minute <= 30)
            ):
                await check_price_alerts(db)
                
        except Exception as e:
            logger.error(f"[Telegram Scheduler] Error in scheduler loop: {e}")
        finally:
            db.close()
            
        # Sleep 30 seconds before next time check (safely handles KST hour/minute transitions)
        await asyncio.sleep(30)
