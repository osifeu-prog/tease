from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String(64), index=True, nullable=True)
    bnb_address = Column(String(128), nullable=True)
    balance_slh = Column(Numeric(24, 8), nullable=False, default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, nullable=True)
    to_user_id = Column(Integer, nullable=True)
    tx_type = Column(String(64), nullable=False)
    amount_slh = Column(Numeric(24, 8), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
