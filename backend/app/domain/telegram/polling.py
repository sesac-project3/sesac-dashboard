import asyncio
import logging
import httpx
from sqlalchemy import select
from app.core.config import settings
from app.core.redis import redis_client
from app.core.database import SessionLocal
from app.domain.auth.models import User

logger = logging.getLogger(__name__)

async def run_telegram_polling(stop_event: asyncio.Event):
    if not settings.telegram_bot_token:
        logger.warning("[Telegram Polling] TELEGRAM_BOT_TOKEN is not set. Polling disabled.")
        return

    logger.info("[Telegram Polling] Starting Telegram bot polling...")
    offset = 0
    
    async def send_msg(chat_id: str, text: str):
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    url, 
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, 
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"[Telegram Polling] Send message failed: {e}")

    while not stop_event.is_set():
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
        params = {"offset": offset, "timeout": 5}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, params=params, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            offset = update.get("update_id") + 1
                            message = update.get("message")
                            if not message:
                                continue
                            
                            chat_id = str(message.get("chat", {}).get("id", ""))
                            text = str(message.get("text", "")).strip()
                            
                            if not chat_id or not text:
                                continue
                                
                            if text.startswith("/start"):
                                parts = text.split(" ")
                                if len(parts) > 1:
                                    link_code = parts[1].strip()
                                    user_id_str = redis_client.get(f"tg_link:{link_code}")
                                    if user_id_str:
                                        user_id = int(user_id_str)
                                        db = SessionLocal()
                                        try:
                                            user = db.scalar(select(User).where(User.id == user_id))
                                            if user:
                                                user.telegram_chat_id = chat_id
                                                db.commit()
                                                redis_client.delete(f"tg_link:{link_code}")
                                                await send_msg(
                                                    chat_id,
                                                    "<b>안녕하세요! 새싹 주식 대시보드 알림 서비스입니다.</b>\n\n성공적으로 연동되었습니다! 앞으로 실시간 주가 급등락 시그널 및 매일 정기 요약 브리핑을 이 채널을 통해 알려드립니다."
                                                )
                                                logger.info(f"[Telegram Polling] Successfully linked user {user_id} with chat_id {chat_id}")
                                            else:
                                                await send_msg(chat_id, "연동에 실패했습니다. 유효하지 않은 회원 정보입니다.")
                                        except Exception as db_err:
                                            logger.error(f"[Telegram Polling] DB Error: {db_err}")
                                        finally:
                                            db.close()
                                    else:
                                        await send_msg(chat_id, "만료되었거나 존재하지 않는 연동 코드입니다. 대시보드 화면에서 코드를 새로 발급받아 시작해주세요.")
                                else:
                                    await send_msg(
                                        chat_id,
                                        "<b>반갑습니다! 새싹 주식 대시보드 알림용 봇입니다.</b>\n\n연동을 완료하시려면 웹 대시보드에서 알림 연동 버튼을 누르고 발급된 딥링크를 통해 시작해주세요."
                                    )
                            else:
                                await send_msg(
                                    chat_id,
                                    "이 채널은 알림 전송 전용 채널입니다. 실시간 시장 브리핑 또는 관심종목 경보 발생 시 자동으로 메시지가 전달됩니다."
                                )
        except httpx.RequestError:
            # Network timeouts are expected during polling
            pass
        except Exception as e:
            logger.error(f"[Telegram Polling] Error in polling loop: {e}")
            
        await asyncio.sleep(1)
