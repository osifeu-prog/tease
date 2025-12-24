import secrets
from decimal import Decimal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- חובה לבוט ---
    BOT_TOKEN: str | None = None

    # canonical: DATABASE_URL
    # also accept: database_url (legacy)
    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    SECRET_KEY: str = secrets.token_urlsafe(32)

    # אדמין
    ADMIN_USER_ID: str | None = None

    # כתובת בסיס לWebhook (למשל: https://xxx.up.railway.app)
    WEBHOOK_URL: str | None = None

    # --- ארנק קהילתי / טוקן ---
    COMMUNITY_WALLET_ADDRESS: str | None = None
    COMMUNITY_WALLET_PRIVATE_KEY: str | None = None

    SLH_TOKEN_ADDRESS: str | None = None
    SLH_TOKEN_DECIMALS: int = 18
    SLH_PRICE_NIS: Decimal = Decimal("444")

    # --- BSC / On-chain ---
    BSC_RPC_URL: str | None = None
    BSC_SCAN_BASE: str | None = "https://bscscan.com"

    # --- לינקים חיצוניים ---
    BUY_BNB_URL: str | None = None
    STAKING_INFO_URL: str | None = None
    DOCS_URL: str | None = None
    PUBLIC_BASE_URL: str | None = None

    # --- קבוצות / לוגים בטלגרם ---
    MAIN_COMMUNITY_CHAT_ID: str | None = None
    LOG_NEW_USERS_CHAT_ID: str | None = None
    LOG_TRANSACTIONS_CHAT_ID: str | None = None
    LOG_ERRORS_CHAT_ID: str | None = None
    REFERRAL_LOGS_CHAT_ID: str | None = None

    # --- שפות ---
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: str | None = None  # "en,he,ru,es"

    @property
    def database_url(self) -> str | None:
        # backward compatible accessor
        return self.DATABASE_URL


settings = Settings()