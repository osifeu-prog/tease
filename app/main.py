from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

from app.database import init_db, SessionLocal
from app.core.config import settings
from app import models
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



@app.get("/debug/status")
async def debug_status(secret: str | None = None) -> dict:
    """Lightweight internal status endpoint.

    Protects itself with a simple shared secret – by default the first 8 chars
    of SECRET_KEY. You can override by passing any string and checking it here.
    """
    expected = (settings.SECRET_KEY or "")[:8]
    if not secret or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check DB connectivity
    db_ok = False
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    finally:
        try:
            db.close()
        except Exception:
            pass

    return {
        "webhook_url": settings.WEBHOOK_URL,
        "bot_token_set": bool(settings.BOT_TOKEN),
        "database_url_set": bool(settings.DATABASE_URL),
        "docs_url": settings.DOCS_URL,
        "public_base_url": settings.PUBLIC_BASE_URL,
        "database_ok": db_ok,
    }


@app.get("/personal/{telegram_id}", response_class=HTMLResponse)
async def personal_page(telegram_id: int):
    """Simple public investor page – can be turned into a full site later."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    finally:
        db.close()

    if not user:
        raise HTTPException(status_code=404, detail="Unknown investor.")

    # Note: we intentionally do not expose confidential data – only public-facing info.
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Investor #{telegram_id}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 2rem; background:#050816; color:#f9fafb; }}
    .card {{ max-width: 640px; margin: 0 auto; padding: 2rem; border-radius: 1.5rem; background: radial-gradient(circle at top, #111827 0, #020617 60%); box-shadow: 0 24px 80px rgba(15,23,42,.9); border:1px solid rgba(148,163,184,.35); }}
    h1 {{ margin-top: 0; font-size: 1.9rem; }}
    .muted {{ color:#9ca3af; font-size:.9rem; }}
    .label {{ font-size:.8rem; text-transform: uppercase; letter-spacing:.09em; color:#a5b4fc; }}
    .value {{ font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }}
    .chip {{ display:inline-flex; align-items:center; padding:.25rem .75rem; border-radius:999px; background:rgba(55,65,81,.7); font-size:.75rem; margin-right:.5rem; }}
  </style>
</head>
<body>
  <main class="card">
    <div class="muted">SLH · Investor Node</div>
    <h1>Community Investor #{telegram_id}</h1>
    <p class="muted">This is a public, read‑only card for one investor node in the SLH ecosystem.</p>

    <p class="label">Telegram</p>
    <p class="value">@{user.username or telegram_id}</p>

    <p class="label">BNB / SLH Wallet</p>
    <p class="value">{user.bnb_address or 'Not yet linked'}</p>

    <p class="label">Internal Ledger Balance (SLH)</p>
    <p class="value">{user.balance_slh:.4f} SLH</p>

    <p class="muted" style="margin-top:1.5rem;">
      No actions can be taken from this page – it is a public display only.
      To operate on/off chain, use the Telegram bot directly.
    </p>

    <p style="margin-top:1.5rem;">
      <span class="chip">On‑chain: BNB Smart Chain</span>
      <span class="chip">Off‑chain: Internal SLH ledger</span>
    </p>
  </main>
</body>
</html>"""  # noqa: E501

    return HTMLResponse(content=html)


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    נקודת ה-webhook של טלגרם.
    טלגרם שולח לכאן עדכונים, ואנחנו מעבירים אותם ל-process_webhook.
    """
    update_dict = await request.json()
    await process_webhook(update_dict)
    return JSONResponse({"ok": True}, status_code=status.HTTP_200_OK)
