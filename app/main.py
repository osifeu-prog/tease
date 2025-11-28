from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.database import init_db
from app.bot.investor_wallet_bot import initialize_bot, process_webhook

# יצירת אפליקציית FastAPI
app = FastAPI(title="SLH Investor Gateway")


@app.on_event("startup")
async def startup_event():
    """
    רץ פעם אחת כאשר השרת עולה:
    1. מוודא שהטבלאות (users, transactions) קיימות.
    2. מאתחל את בוט הטלגרם וקובע webhook.
    """
    # יצירת טבלאות חסרות (לא מוחק / לא משכתב קיימות)
    init_db()

    # אתחול בוט הטלגרם (Application + webhook לפי WEBHOOK_URL)
    await initialize_bot()


@app.get("/")
async def root():
    """
    סתם דף בית קטן – אפשר להשתמש לבדיקה מהירה שהאפליקציה חיה.
    """
    return {"message": "SLH Investor Gateway is running"}


@app.get("/health")
async def health():
    """
    מסלול healthcheck לריילווי.
    """
    return {"status": "ok"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    נקודת ה-webhook של טלגרם.
    טלגרם שולח לכאן עדכונים, ואנחנו מעבירים אותם ל-process_webhook.
    """
    update_dict = await request.json()
    await process_webhook(update_dict)
    return JSONResponse({"ok": True}, status_code=status.HTTP_200_OK)
