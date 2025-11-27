from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# יצירת engine מול ה-Postgres מריילווי
engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    pool_pre_ping=True,  # מונע בעיות חיבור מתות
)

# Session של SQLAlchemy לעבודה מול ה-DB
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# בסיס המודלים
Base = declarative_base()


def init_db():
    """
    יצירת טבלאות חסרות (users, transactions וכו') לפי המודלים.
    לא נוגע בטבלאות קיימות.
    """
    # חשוב לייבא את המודלים כדי ש-SQLAlchemy יכיר את הטבלאות
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency סטנדרטי למי שרוצה להשתמש ב-Session דרך FastAPI.
    (כרגע לא חובה, אבל טוב שיהיה לעתיד.)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
