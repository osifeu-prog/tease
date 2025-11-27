from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    # Railway תמיד מעבירה DATABASE_URL, אבל לפיתוח לוקאלי אפשר לשים sqlite כברירת מחדל
    DATABASE_URL = "sqlite:///./bot_factory.db"

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def init_db():
    # יבוא כאן כדי להימנע מתלות מעגלית
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
