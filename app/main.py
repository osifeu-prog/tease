
# --- SLH SAFETY: ignore non-private updates at webhook (groups/channels) ---
def _slh_is_private_update(payload: dict) -> bool:
    try:
        msg = payload.get("message") or payload.get("edited_message") or payload.get("channel_post") or payload.get("edited_channel_post")
        if isinstance(msg, dict):
            chat = msg.get("chat") or {}
            return chat.get("type") == "private"

        cb = payload.get("callback_query")
        if isinstance(cb, dict):
            m2 = cb.get("message") or {}
            chat = m2.get("chat") or {}
            return chat.get("type") == "private"

        # If we cannot detect chat type, do not block.
        return True
    except Exception:
        return True
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.database import init_db
from app.bot.investor_wallet_bot import initialize_bot, process_webhook
from app.monitoring import run_selftest

app = FastAPI(title="SLH Investor Gateway")


@app.on_event("startup")
async def startup_event():
    """
    ×¨×¥ ×¤×¢×‌ ×گ×—×ھ ×›×گ×©×¨ ×”×©×¨×ھ ×¢×•×œ×”:
    1. ×‍×•×•×“×گ ×©×”×ک×‘×œ×گ×•×ھ (users, transactions) ×§×™×™×‍×•×ھ.
    2. ×‍×گ×ھ×—×œ ×گ×ھ ×‘×•×ک ×”×ک×œ×’×¨×‌ ×•×§×•×‘×¢ webhook.
    """
    init_db()
    await initialize_bot()


@app.get("/")
async def root():
    return {"message": "SLH Investor Gateway is running"}


@app.get("/health")
async def health():
    """
    ×‍×،×œ×•×œ healthcheck ×‘×،×™×،×™ ×œ×¨×™×™×œ×•×•×™.
    """
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """
    ×‘×“×™×§×ھ ×‍×•×›× ×•×ھ ×‍×”×™×¨×”:
    - DB
    - ENV
    - ×ک×•×§×ں ×ک×œ×’×¨×‌ ×§×™×™×‌
    (×‘×œ×™ getMe, ×›×“×™ ×©×™×”×™×” ×‍×”×™×¨ ×•×§×œ ×œ× ×™×ک×•×¨).
    """
    result = run_selftest(quick=True)
    return {"status": result["status"], "checks": result["checks"]}


@app.get("/selftest")
async def selftest():
    """
    ×‘×“×™×§×” ×¢×‍×•×§×”: DB, ENV, Telegram, BSC.
    ×گ×¤×©×¨ ×œ×¤×ھ×•×— ×‘×“×¤×“×¤×ں ×œ×§×‘×œ ×“×•"×—.
    """
    return run_selftest(quick=False)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    × ×§×•×“×ھ ×”-webhook ×©×œ ×ک×œ×’×¨×‌.
    ×ک×œ×’×¨×‌ ×©×•×œ×— ×œ×›×گ×ں ×¢×“×›×•× ×™×‌, ×•×گ× ×—× ×• ×‍×¢×‘×™×¨×™×‌ ×گ×•×ھ×‌ ×œ-process_webhook.
    """
    update_dict = await request.json()
    # SLH SAFETY: ignore groups/channels
    if not _slh_is_private_update(payload if 'payload' in locals() else data if 'data' in locals() else update if 'update' in locals() else locals().get('update_json', {})):
        return { "ok": True, "ignored": "non-private" }
    await process_webhook(update_dict)
    return JSONResponse({"ok": True}, status_code=status.HTTP_200_OK)
