import logging
import json
from typing import Any, Dict, List
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from telegram import Bot
from sqlalchemy import text

from app.database import SessionLocal
from app.core.config import settings
from app import blockchain

logger = logging.getLogger(__name__)


def _check_database(checks: Dict[str, Any]) -> str:
    status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except Exception as e:
        logger.exception("Database selftest failed: %s", e)
        checks["database"] = {"ok": False, "error": str(e)}
        status = "error"
    finally:
        try:
            db.close()
        except Exception:
            pass
    return status


def _check_env(checks: Dict[str, Any]) -> str:
    status = "ok"
    missing: List[str] = []

    required = [
        "BOT_TOKEN",
        "DATABASE_URL",
        "COMMUNITY_WALLET_ADDRESS",
        "SLH_TOKEN_ADDRESS",
    ]

    for name in required:
        value = getattr(settings, name, None)
        if not value:
            missing.append(name)

    checks["env"] = {
        "ok": len(missing) == 0,
        "missing": missing,
    }

    if missing:
        status = "degraded"

    return status


def _check_telegram(checks: Dict[str, Any], quick: bool) -> str:
    """
    בדיקת טלגרם:

    quick=True  -> רק לוודא שיש BOT_TOKEN.
    quick=False -> קריאת getMe ישירות ל-HTTP API של טלגרם (סינכרוני).
    """
    status = "ok"

    if not settings.BOT_TOKEN:
        checks["telegram"] = {
            "ok": False,
            "error": "BOT_TOKEN not configured",
        }
        return "degraded"

    if quick:
        checks["telegram"] = {"ok": True}
        return "ok"

    try:
        url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/getMe"
        with urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("ok"):
            checks["telegram"] = {
                "ok": False,
                "error": str(data),
            }
            status = "error"
        else:
            result = data.get("result", {})
            checks["telegram"] = {
                "ok": True,
                "username": result.get("username"),
                "id": result.get("id"),
            }
    except (HTTPError, URLError) as e:
        logger.exception("Telegram selftest failed (HTTP): %s", e)
        checks["telegram"] = {"ok": False, "error": str(e)}
        status = "error"
    except Exception as e:
        logger.exception("Telegram selftest failed: %s", e)
        checks["telegram"] = {"ok": False, "error": str(e)}
        status = "error"

    return status


def _check_bsc(checks: Dict[str, Any]) -> str:
    status = "ok"

    if not settings.BSC_RPC_URL or not settings.COMMUNITY_WALLET_ADDRESS:
        checks["bsc"] = {
            "ok": False,
            "skipped": True,
            "reason": "BSC_RPC_URL or COMMUNITY_WALLET_ADDRESS missing",
        }
        return "degraded"

    try:
        on = blockchain.get_onchain_balances(settings.COMMUNITY_WALLET_ADDRESS)
        if on is None:
            checks["bsc"] = {
                "ok": False,
                "error": "Unable to fetch on-chain balances (RPC or address error).",
            }
            status = "degraded"
        else:
            checks["bsc"] = {
                "ok": True,
                "bnb": str(on.get("bnb")),
                "slh": str(on.get("slh")),
            }
    except Exception as e:
        logger.exception("BSC selftest failed: %s", e)
        checks["bsc"] = {"ok": False, "error": str(e)}
        status = "error"

    return status


def run_selftest(quick: bool = False) -> Dict[str, Any]:
    """
    מפעיל בדיקות בריאות על:
    - DB
    - ENV חיוניים
    - Telegram Bot
    - BSC RPC + Community Wallet

    quick=True -> בדיקה מהירה (בלי getMe).
    """
    checks: Dict[str, Any] = {}
    overall = "ok"

    st = _check_database(checks)
    if st == "error":
        overall = "error"
    elif st == "degraded" and overall == "ok":
        overall = "degraded"

    st = _check_env(checks)
    if st == "error":
        overall = "error"
    elif st == "degraded" and overall == "ok":
        overall = "degraded"

    st = _check_telegram(checks, quick=quick)
    if st == "error":
        overall = "error"
    elif st == "degraded" and overall == "ok":
        overall = "degraded"

    st = _check_bsc(checks)
    if st == "error":
        overall = "error"
    elif st == "degraded" and overall == "ok":
        overall = "degraded"

    return {
        "status": overall,
        "checks": checks,
    }
