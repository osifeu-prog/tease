import logging

from fastapi import FastAPI, Request

from app.database import init_db
from app.bot.investor_wallet_bot import initialize_bot, process_webhook

logger = logging.getLogger("app.main")

app = FastAPI(title="SLH Investor Gateway Bot")


@app.on_event("startup")
async def on_startup():
    logger.info("Initializing database...")
    init_db()
    logger.info("Initializing Telegram bot...")
    await initialize_bot()
    logger.info("Startup complete.")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    await process_webhook(data)
    # Telegram expects a 200 OK quickly
    return {"ok": True}
