from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Numeric,
    DateTime,
    Integer,
)
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    טבלת משתמשים – מותאם לסכימה הקיימת בפוסטגרס.

    חשוב:
    - אין עמודה id.
    - telegram_id הוא ה-Primary Key.
    """

    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), index=True, nullable=True)
    bnb_address = Column(String(255), nullable=True)
    balance_slh = Column(Numeric(24, 6), nullable=False, default=0)


class Transaction(Base):
    """
    טבלת טרנזקציות פנימיות (Off-Chain Ledger).
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # מזהי טלגרם (לא FK פורמלי, פשוט שמירה של ה-ID)
    from_user = Column(BigInteger, nullable=True)
    to_user = Column(BigInteger, nullable=True)

    amount_slh = Column(Numeric(24, 6), nullable=False)
    tx_type = Column(String(50), nullable=False)
