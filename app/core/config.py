import secrets
from decimal import Decimal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- חובה לבוט ---
    BOT_TOKEN: str | None = None
    DATABASE_URL: str | None = None
    SECRET_KEY: str = secrets.token_urlsafe(32)

    # אדמין (לפקודות admin_credit / admin_menu)
    ADMIN_USER_ID: str | None = None

    # כתובת בסיס ל־Webhook (למשל: https://tease-production.up.railway.app)
    WEBHOOK_URL: str | None = None

    # --- הגדרות SLH / BSC / דוקומנטציה ---

    # ארנק קהילה (לקבלות / מעקב השקעות)
    COMMUNITY_WALLET_ADDRESS: str | None = None

    # כתובת טוקן SLH על BSC
    SLH_TOKEN_ADDRESS: str | None = None

    # מחיר נומינלי של SLH בש"ח (למשקיעים) – ברירת מחדל 444
    SLH_PRICE_NIS: Decimal | int | float = 444

    # RPC של BSC mainnet – לדוגמה:
    # https://bsc-dataseed.binance.org
    BSC_RPC_URL: str | None = None

    # כתובת בסיס של BscScan
    BSC_SCAN_BASE: str | None = "https://bscscan.com"

    # לינק חיצוני לקניית BNB (Binance / שירות אחר)
    BUY_BNB_URL: str | None = None

    # לינק חיצוני למידע על Staking (אפשר דף באתר שלך)
    STAKING_INFO_URL: str | None = None

    # לינק לדפי DOCS של המשקיעים (GitHub Pages וכו')
    DOCS_URL: str | None = None

    # מספר דצימלים של טוקן SLH ברשת (לפי החוזה – כרגע הגדרנו 15 ב-ENV)
    SLH_TOKEN_DECIMALS: int = 18

    # --- Telegram groups / channels for logs & management ---
    # IDs can be integers or strings (e.g. '-100123456789'); set only what you use.
    MAIN_COMMUNITY_CHAT_ID: str | None = None
    LOG_NEW_USERS_CHAT_ID: str | None = None
    LOG_TRANSACTIONS_CHAT_ID: str | None = None
    LOG_ERRORS_CHAT_ID: str | None = None
    REFERRAL_LOGS_CHAT_ID: str | None = None

    # Base URL for public personal pages / landing (optional).
    # If not set, DOCS_URL or WEBHOOK_URL will be used as fallback where relevant.
    PUBLIC_BASE_URL: str | None = None

    # Optional private key of the community wallet (hot wallet for faucet / admin sends).
    # WARNING: use only a dedicated hot wallet with limited funds.
    COMMUNITY_WALLET_PRIVATE_KEY: str | None = None

    # Language defaults (auto-detect from Telegram language_code, with this fallback).
    DEFAULT_LANGUAGE: str = "he"
    SUPPORTED_LANGUAGES: str | None = "he,en,ru,es"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()