import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database import engine
from app.models import Base
from app.bot.investor_wallet_bot import initialize_bot, process_webhook

logger = logging.getLogger(__name__)

# יצירת טבלאות אם אינן קיימות
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SLH Investor Gateway",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """
    מופעל אוטומטית כשהשרת עולה – כאן אנחנו מאתחלים את הבוט.
    """
    logger.info("🚀 FastAPI startup – initializing Telegram InvestorWalletBot...")
    await initialize_bot()
    logger.info("✅ Telegram bot initialized and webhook (if configured) is ready.")


@app.get("/")
async def root():
    return {
        "service": "SLH Investor Gateway",
        "status": "ok",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    נקודת ה-Webhook שאליה Telegram שולח עדכונים.
    """
    data = await request.json()
    await process_webhook(data)
    return JSONResponse({"ok": True})
