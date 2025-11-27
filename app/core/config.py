from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core
    BOT_TOKEN: str | None = None
    WEBHOOK_URL: str | None = None

    # Database
    DATABASE_URL: str

    # SLH / BNB config
    COMMUNITY_WALLET_ADDRESS: str | None = None
    SLH_TOKEN_ADDRESS: str | None = None
    SLH_PRICE_NIS: float = 444.0

    BSC_SCAN_BASE: str | None = "https://bscscan.com"
    BUY_BNB_URL: str | None = "https://www.binance.com/en/buy-BNB"
    STAKING_INFO_URL: str | None = None

    # Docs
    DOCS_URL: str | None = None

    # Admin
    ADMIN_USER_ID: int | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
