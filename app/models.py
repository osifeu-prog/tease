from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    bnb_address = Column(String(255), nullable=True)
    balance_slh = Column(Numeric(24, 6), nullable=False, default=Decimal("0"))


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # מזהי טלגרם (לא FK) כדי לא לסבך
    from_user = Column(Integer, nullable=True)
    to_user = Column(Integer, nullable=True)
    amount_slh = Column(Numeric(24, 6), nullable=False)
    tx_type = Column(String(50), nullable=False)
