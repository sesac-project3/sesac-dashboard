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
from app.domain.reports.service import report_service
from app.domain.telegram.models import TelegramNotification
from app.domain.telegram.router import send_telegram_message

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

async def send_morning_briefing(db: Session, force: bool = False):
    logger.info("[Telegram Scheduler] Dispatching Morning Briefing (08:00)...")
    today_date = date.today()
    
    indices = fetch_index_details()
    kospi_val, kosdaq_val = None, None
    for idx in indices:
        if idx.indexType == "KOSPI":
            kospi_val = idx
        elif idx.indexType == "KOSDAQ":
            kosdaq_val = idx

    def fmt_index(idx):
        if not idx:
            return "N/A"
        arrow = "▲" if idx.isUp else "▼"
        sign = "+" if idx.isUp else ""
        return f"{idx.value:,.2f}  {arrow} {sign}{idx.changePercent:.2f}%"

    stock_items = fetch_stock_ranking_items(db)
    price_by_code = {item.code: item for item in stock_items}

    users = db.scalars(select(User).where(User.telegram_chat_id != None)).all()
    for user in users:
        if not force:
            existing = db.scalar(
                select(TelegramNotification).where(
                    TelegramNotification.user_id == user.id,
                    TelegramNotification.notification_type == "조간_브리핑",
                    TelegramNotification.sent_date == today_date
                )
            )
            if existing:
                continue

        # Skip if user has disabled morning briefing
        if not user.notify_morning:
            continue

        watchlist_stocks = db.scalars(
            select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user.id)
        ).all()

        watchlist_lines = ""
        if watchlist_stocks:
            from urllib.parse import quote
            for stock in watchlist_stocks:
                item = price_by_code.get(stock.code)
                price_str = f"{item.price:,.0f}원" if item else "가격정보 없음"
                naver_url = f"https://search.naver.com/search.naver?where=news&query={quote(stock.name)}"
                watchlist_lines += (
                    f"  <b>{stock.name}</b>  <code>{stock.code}</code>\n"
                    f"  💵 전일가 {price_str}  |  📰 <a href=\"{naver_url}\">뉴스 검색</a>\n\n"
                )
        else:
            watchlist_lines = "  등록된 관심종목이 없습니다.\n"

        briefing_text = (
            f"🌅 <b>오전 시장 브리핑</b>\n"
            f"<i>{today_date.strftime('%Y년 %m월 %d일')} · 개장 전 요약</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>전일 국내 증시 마감</b>\n"
            f"  코스피  {fmt_index(kospi_val)}\n"
            f"  코스닥  {fmt_index(kosdaq_val)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"👀 <b>관심종목 개장 전 체크</b>\n\n"
            f"{watchlist_lines}"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 개장 전 최신 뉴스를 확인하고 시황 변동성에 대비하세요.\n"
            f"오늘도 성공적인 투자 되세요! 🚀"
        )

        try:
            await send_telegram_message(user.telegram_chat_id, briefing_text)
            if not force:
                log_entry = TelegramNotification(
                    user_id=user.id,
                    notification_type="조간_브리핑",
                    sent_date=today_date
                )
                db.add(log_entry)
                db.commit()
        except Exception as e:
            logger.error(f"[Telegram Scheduler] Failed to send morning briefing to user {user.id}: {e}")
            db.rollback()

async def send_evening_briefing(db: Session, force: bool = False):
    logger.info("[Telegram Scheduler] Dispatching Evening Briefing (16:30)...")
    today_date = date.today()
    
    indices = fetch_index_details()
    kospi_val, kosdaq_val = None, None
    for idx in indices:
        if idx.indexType == "KOSPI":
            kospi_val = idx
        elif idx.indexType == "KOSDAQ":
            kosdaq_val = idx

    def fmt_index(idx):
        if not idx:
            return "N/A"
        arrow = "▲" if idx.isUp else "▼"
        sign = "+" if idx.isUp else ""
        return f"{idx.value:,.2f}  {arrow} {sign}{idx.changePercent:.2f}%"

    stock_items = fetch_stock_ranking_items(db)
    price_by_code = {item.code: item for item in stock_items}

    users = db.scalars(select(User).where(User.telegram_chat_id != None)).all()
    for user in users:
        if not force:
            existing = db.scalar(
                select(TelegramNotification).where(
                    TelegramNotification.user_id == user.id,
                    TelegramNotification.notification_type == "마감_브리핑",
                    TelegramNotification.sent_date == today_date
                )
            )
            if existing:
                continue

        # Skip if user has disabled evening briefing
        if not user.notify_evening:
            continue

        watchlist_stocks = db.scalars(
            select(Stock).join(Watchlist, Watchlist.stock_id == Stock.id).where(Watchlist.user_id == user.id)
        ).all()

        watchlist_lines = ""
        if watchlist_stocks:
            for stock in watchlist_stocks:
                item = price_by_code.get(stock.code)
                report = report_service.get_stock_report(db, stock.code)
                judgement = report.judgement if report else "관망"
                if item:
                    arrow = "▲" if item.changePercent >= 0 else "▼"
                    sign = "+" if item.changePercent >= 0 else ""
                    ai_emoji = "🟢" if "매수" in judgement else ("🔴" if "매도" in judgement else "🟡")
                    watchlist_lines += (
                        f"  <b>{stock.name}</b>  <code>{stock.code}</code>\n"
                        f"  💵 {item.price:,.0f}원  {arrow} {sign}{item.changePercent:.2f}%\n"
                        f"  {ai_emoji} AI 의견: <b>{judgement}</b>\n\n"
                    )
                else:
                    watchlist_lines += f"  <b>{stock.name}</b>  <code>{stock.code}</code>\n  가격 정보 없음\n\n"
        else:
            watchlist_lines = "  등록된 관심종목이 없습니다.\n"

        briefing_text = (
            f"🌆 <b>장 마감 브리핑</b>\n"
            f"<i>{today_date.strftime('%Y년 %m월 %d일')} · 마감 결과 요약</i>\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>오늘 시장 지수 마감</b>\n"
            f"  코스피  {fmt_index(kospi_val)}\n"
            f"  코스닥  {fmt_index(kosdaq_val)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 <b>관심종목 마감 결과 &amp; AI 의견</b>\n\n"
            f"{watchlist_lines}"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💡 상세 분석은 대시보드에서 확인하세요.\n"
            f"내일도 성공적인 투자 되세요! 🙌"
        )

        try:
            await send_telegram_message(user.telegram_chat_id, briefing_text)
            if not force:
                log_entry = TelegramNotification(
                    user_id=user.id,
                    notification_type="마감_브리핑",
                    sent_date=today_date
                )
                db.add(log_entry)
                db.commit()
        except Exception as e:
            logger.error(f"[Telegram Scheduler] Failed to send evening briefing to user {user.id}: {e}")
            db.rollback()


async def check_price_alerts(db: Session, force: bool = False):
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

            # Skip if user has disabled price alerts
            if not user.notify_alert:
                continue

            # Check relative change vs market index
            market_type = "KOSDAQ" if stock.market == "KOSDAQ" else "KOSPI"
            index_change = index_change_by_market.get(market_type, 0.0)
            relative_change = item.changePercent - index_change

            # Threshold: Relative change exceeds ±3%p OR absolute change exceeds ±5%
            exceeds_relative = abs(relative_change) >= 3.0
            exceeds_absolute = abs(item.changePercent) >= 5.0

            # In force mode (test), skip threshold check; otherwise apply it
            if not force and not (exceeds_relative or exceeds_absolute):
                continue

            # Check if already alert sent today for this stock to this user (skip when force=True)
            if not force:
                existing = db.scalar(
                    select(TelegramNotification).where(
                        TelegramNotification.user_id == user.id,
                        TelegramNotification.notification_type == "시그널",
                        TelegramNotification.stock_id == stock.id,
                        TelegramNotification.sent_date == today_date
                    )
                )
                if existing:
                    continue

            direction = "📈 급등" if relative_change >= 0 else "📉 급락"
            arrow = "▲" if item.changePercent >= 0 else "▼"
            sign = "+" if item.changePercent >= 0 else ""
            diff_sign = "+" if relative_change >= 0 else ""
            perf_label = "아웃퍼폼 🔥" if relative_change >= 0 else "언더퍼폼 🧊"

            alert_text = (
                f"🚨 <b>관심종목 급변동 경보</b>\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"{direction}  <b>{stock.name}</b>  <code>{stock.code}</code>\n\n"
                f"💵 현재가: <b>{item.price:,.0f}원</b>\n"
                f"  {arrow} 당일 등락: <b>{sign}{item.changePercent:.2f}%</b>\n"
                f"  📊 {market_type} 지수 대비: <b>{diff_sign}{relative_change:.2f}%p</b>  →  {perf_label}\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💡 지수 대비 큰 변동이 감지되었습니다. 대시보드에서 상세 내용을 확인하세요."
            )

            try:
                await send_telegram_message(user.telegram_chat_id, alert_text)
                if not force:
                    log_entry = TelegramNotification(
                        user_id=user.id,
                        notification_type="시그널",
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
