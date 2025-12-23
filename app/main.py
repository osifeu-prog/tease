BUILD_ID = os.getenv("BUILD_ID", "local-dev")
import os

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
    ط£â€”ط¢آ¨ط£â€”ط¢آ¥ ط£â€”ط¢آ¤ط£â€”ط¢آ¢ط£â€”أ¢â‚¬إ’ ط£â€”ط¹آ¯ط£â€”أ¢â‚¬â€‌ط£â€”ط¹آ¾ ط£â€”أ¢â‚¬ط›ط£â€”ط¹آ¯ط£â€”ط¢آ©ط£â€”ط¢آ¨ ط£â€”أ¢â‚¬â€Œط£â€”ط¢آ©ط£â€”ط¢آ¨ط£â€”ط¹آ¾ ط£â€”ط¢آ¢ط£â€”أ¢â‚¬آ¢ط£â€”ط¥â€œط£â€”أ¢â‚¬â€Œ:
    1. ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬إ“ط£â€”ط¹آ¯ ط£â€”ط¢آ©ط£â€”أ¢â‚¬â€Œط£â€”ط¹آ©ط£â€”أ¢â‚¬ع©ط£â€”ط¥â€œط£â€”ط¹آ¯ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ¾ (users, transactions) ط£â€”ط¢آ§ط£â€”أ¢â€‍آ¢ط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ¾.
    2. ط£â€”أ¢â‚¬ع†ط£â€”ط¹آ¯ط£â€”ط¹آ¾ط£â€”أ¢â‚¬â€‌ط£â€”ط¥â€œ ط£â€”ط¹آ¯ط£â€”ط¹آ¾ ط£â€”أ¢â‚¬ع©ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ© ط£â€”أ¢â‚¬â€Œط£â€”ط¹آ©ط£â€”ط¥â€œط£â€”أ¢â‚¬â„¢ط£â€”ط¢آ¨ط£â€”أ¢â‚¬إ’ ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ§ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬ع©ط£â€”ط¢آ¢ webhook.
    """
    init_db()
    await initialize_bot()


@app.get("/")
async def root():
    return {"message": "SLH Investor Gateway is running"}


@app.get("/health")
async def health():
    return {"status": "ok", "build_id": BUILD_ID}
@app.get("/ready")
async def ready():
    """
    ط£â€”أ¢â‚¬ع©ط£â€”أ¢â‚¬إ“ط£â€”أ¢â€‍آ¢ط£â€”ط¢آ§ط£â€”ط¹آ¾ ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬ط›ط£â€”ط¢آ ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ¾ ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬â€Œط£â€”أ¢â€‍آ¢ط£â€”ط¢آ¨ط£â€”أ¢â‚¬â€Œ:
    - DB
    - ENV
    - ط£â€”ط¹آ©ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ§ط£â€”ط¹ط› ط£â€”ط¹آ©ط£â€”ط¥â€œط£â€”أ¢â‚¬â„¢ط£â€”ط¢آ¨ط£â€”أ¢â‚¬إ’ ط£â€”ط¢آ§ط£â€”أ¢â€‍آ¢ط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬إ’
    (ط£â€”أ¢â‚¬ع©ط£â€”ط¥â€œط£â€”أ¢â€‍آ¢ getMe, ط£â€”أ¢â‚¬ط›ط£â€”أ¢â‚¬إ“ط£â€”أ¢â€‍آ¢ ط£â€”ط¢آ©ط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬â€Œط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬â€Œ ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬â€Œط£â€”أ¢â€‍آ¢ط£â€”ط¢آ¨ ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ§ط£â€”ط¥â€œ ط£â€”ط¥â€œط£â€”ط¢آ ط£â€”أ¢â€‍آ¢ط£â€”ط¹آ©ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ¨).
    """
    result = run_selftest(quick=True)
    return {"status": result["status"], "checks": result["checks"]}


@app.get("/selftest")
async def selftest():
    """
    ط£â€”أ¢â‚¬ع©ط£â€”أ¢â‚¬إ“ط£â€”أ¢â€‍آ¢ط£â€”ط¢آ§ط£â€”أ¢â‚¬â€Œ ط£â€”ط¢آ¢ط£â€”أ¢â‚¬ع†ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ§ط£â€”أ¢â‚¬â€Œ: DB, ENV, Telegram, BSC.
    ط£â€”ط¹آ¯ط£â€”ط¢آ¤ط£â€”ط¢آ©ط£â€”ط¢آ¨ ط£â€”ط¥â€œط£â€”ط¢آ¤ط£â€”ط¹آ¾ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬â€‌ ط£â€”أ¢â‚¬ع©ط£â€”أ¢â‚¬إ“ط£â€”ط¢آ¤ط£â€”أ¢â‚¬إ“ط£â€”ط¢آ¤ط£â€”ط¹ط› ط£â€”ط¥â€œط£â€”ط¢آ§ط£â€”أ¢â‚¬ع©ط£â€”ط¥â€œ ط£â€”أ¢â‚¬إ“ط£â€”أ¢â‚¬آ¢"ط£â€”أ¢â‚¬â€‌.
    """
    return run_selftest(quick=False)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    ط£â€”ط¢آ ط£â€”ط¢آ§ط£â€”أ¢â‚¬آ¢ط£â€”أ¢â‚¬إ“ط£â€”ط¹آ¾ ط£â€”أ¢â‚¬â€Œ-webhook ط£â€”ط¢آ©ط£â€”ط¥â€œ ط£â€”ط¹آ©ط£â€”ط¥â€œط£â€”أ¢â‚¬â„¢ط£â€”ط¢آ¨ط£â€”أ¢â‚¬إ’.
    ط£â€”ط¹آ©ط£â€”ط¥â€œط£â€”أ¢â‚¬â„¢ط£â€”ط¢آ¨ط£â€”أ¢â‚¬إ’ ط£â€”ط¢آ©ط£â€”أ¢â‚¬آ¢ط£â€”ط¥â€œط£â€”أ¢â‚¬â€‌ ط£â€”ط¥â€œط£â€”أ¢â‚¬ط›ط£â€”ط¹آ¯ط£â€”ط¹ط› ط£â€”ط¢آ¢ط£â€”أ¢â‚¬إ“ط£â€”أ¢â‚¬ط›ط£â€”أ¢â‚¬آ¢ط£â€”ط¢آ ط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬إ’, ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ¯ط£â€”ط¢آ ط£â€”أ¢â‚¬â€‌ط£â€”ط¢آ ط£â€”أ¢â‚¬آ¢ ط£â€”أ¢â‚¬ع†ط£â€”ط¢آ¢ط£â€”أ¢â‚¬ع©ط£â€”أ¢â€‍آ¢ط£â€”ط¢آ¨ط£â€”أ¢â€‍آ¢ط£â€”أ¢â‚¬إ’ ط£â€”ط¹آ¯ط£â€”أ¢â‚¬آ¢ط£â€”ط¹آ¾ط£â€”أ¢â‚¬إ’ ط£â€”ط¥â€œ-process_webhook.
    """
    update_dict = await request.json()
    # SLH SAFETY: ignore groups/channels
    if not _slh_is_private_update(payload if 'payload' in locals() else data if 'data' in locals() else update if 'update' in locals() else locals().get('update_json', {})):
        _p = payload if 'payload' in locals() else data if 'data' in locals() else update if 'update' in locals() else locals().get('update_json', {})
        _t,_cid = _slh_chat_fingerprint(_p)
        _uid = str((_p.get('update_id') if isinstance(_p, dict) else None) or '?')
        try:
            import logging as _logging
            _logging.getLogger('slhnet').info(f'SLH SAFETY: ignored non-private update update_id={_uid} chat_type={_t} chat_id={_cid}')
        except Exception:
            pass
        return { "ok": True, "ignored": "non-private", "chat_type": _t }
    # SLH SAFETY: ignore groups/channels
    if not _slh_is_private_update(payload if 'payload' in locals() else data if 'data' in locals() else update if 'update' in locals() else locals().get('update_json', {})):
        return { "ok": True, "ignored": "non-private" }
    await process_webhook(update_dict)
    return JSONResponse({"ok": True}, status_code=status.HTTP_200_OK)
