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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
