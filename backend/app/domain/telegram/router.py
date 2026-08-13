import secrets
import string
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.response import ApiResponse
from app.common.security import get_current_user_id
from app.core.database import get_db
from app.core.config import settings
from app.core.redis import redis_client
from app.domain.auth.models import User

router = APIRouter(prefix="/telegram", tags=["telegram"])

def generate_link_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))

async def send_telegram_message(chat_id: str, text: str):
    if not settings.telegram_bot_token:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=5.0)
    except Exception as e:
        # Silently log errors in console
        print(f"Telegram API Error: {e}")

@router.get("/status", response_model=ApiResponse[dict])
def get_telegram_status(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="사용자 없음")
    
    return ApiResponse.ok({
        "linked": user.telegram_chat_id is not None,
        "botUsername": settings.telegram_bot_username
    })

@router.post("/link-code", response_model=ApiResponse[dict])
def create_link_code(user_id: int = Depends(get_current_user_id)):
    code = generate_link_code()
    # Map code to user_id in Redis with 10-minute expiry (600 seconds)
    redis_client.set(f"tg_link:{code}", user_id, ex=600)
    return ApiResponse.ok({
        "linkCode": code,
        "botUsername": settings.telegram_bot_username
    })

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    message = payload.get("message")
    if not message:
        return {"status": "ok"}

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = str(message.get("text", "")).strip()

    if not chat_id or not text:
        return {"status": "ok"}

    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) > 1:
            link_code = parts[1].strip()
            user_id_str = redis_client.get(f"tg_link:{link_code}")
            
            if user_id_str:
                user_id = int(user_id_str)
                user = db.scalar(select(User).where(User.id == user_id))
                if user:
                    user.telegram_chat_id = chat_id
                    db.commit()
                    redis_client.delete(f"tg_link:{link_code}")
                    background_tasks.add_task(
                        send_telegram_message,
                        chat_id,
                        "<b>안녕하세요! 새싹 주식 대시보드 알림 서비스입니다.</b>\n\n성공적으로 연동되었습니다! 앞으로 실시간 주가 급등락 시그널 및 매일 정기 요약 브리핑을 이 채널을 통해 알려드립니다."
                    )
                else:
                    background_tasks.add_task(
                        send_telegram_message,
                        chat_id,
                        "연동에 실패했습니다. 유효하지 않은 회원 정보입니다."
                    )
            else:
                background_tasks.add_task(
                    send_telegram_message,
                    chat_id,
                    "만료되었거나 존재하지 않는 연동 코드입니다. 대시보드 화면에서 코드를 새로 발급받아 시작해주세요."
                )
        else:
            background_tasks.add_task(
                send_telegram_message,
                chat_id,
                "<b>반갑습니다! 새싹 주식 대시보드 알림용 봇입니다.</b>\n\n연동을 완료하시려면 웹 대시보드에서 알림 연동 버튼을 누르고 발급된 딥링크를 통해 시작해주세요."
            )
    else:
        # Help reply for any other messages
        background_tasks.add_task(
            send_telegram_message,
            chat_id,
            "이 채널은 알림 전송 전용 채널입니다. 실시간 시장 브리핑 또는 관심종목 경보 발생 시 자동으로 메시지가 전달됩니다."
        )

    return {"status": "ok"}


@router.post("/test/morning-briefing", response_model=ApiResponse[str])
async def test_morning_briefing(db: Session = Depends(get_db)):
    from app.domain.telegram.scheduler import send_morning_briefing
    await send_morning_briefing(db)
    return ApiResponse.ok("오전 브리핑 모의 발송이 완료되었습니다.")

@router.post("/test/evening-briefing", response_model=ApiResponse[str])
async def test_evening_briefing(db: Session = Depends(get_db)):
    from app.domain.telegram.scheduler import send_evening_briefing
    await send_evening_briefing(db)
    return ApiResponse.ok("오후 브리핑 모의 발송이 완료되었습니다.")

@router.post("/test/price-alert", response_model=ApiResponse[str])
async def test_price_alert(db: Session = Depends(get_db)):
    from app.domain.telegram.scheduler import check_price_alerts
    await check_price_alerts(db)
    return ApiResponse.ok("주가 지수대비 비교 급변동 경보 모의 체크 및 발송이 완료되었습니다.")

