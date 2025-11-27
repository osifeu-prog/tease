# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app import models

# מנוע SQLAlchemy
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

# Session לכל בקשה / שימוש
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# פונקציה לעבודה בבוט: יצירת Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# יצירת הטבלאות אם הן לא קיימות
models.Base.metadata.create_all(bind=engine)
