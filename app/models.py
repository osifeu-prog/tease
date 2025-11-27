from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Numeric,
    DateTime,
    func,
)
from app.database import Base


class User(Base):
    """
    טבלת users הקיימת ב-DB:
    columns: telegram_id, username, bnb_address, balance_slh
    אין עמודה id ולכן אנחנו עובדים עם telegram_id כ-primary key.
    """
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(50), nullable=True, index=True)
    bnb_address = Column(String(255), nullable=True)
    balance_slh = Column(Numeric(20, 8), nullable=False, default=0)


class Transaction(Base):
    """
    טבלת טרנזקציות פנימית (Off-Chain Ledger).
    שים לב: כאן אני מניח שהטבלה נבנתה בערך בצורה הזאת.
    אם כבר הייתה טבלה קיימת, השמות צריכים להתאים:
      - id
      - from_user
      - to_user
      - tx_type
      - amount_slh
      - created_at
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    # מזהי המשתמשים – אנחנו מאחסנים בהם את ה-telegram_id
    from_user = Column(BigInteger, nullable=True)
    to_user = Column(BigInteger, nullable=True)

    tx_type = Column(String(50), nullable=False)  # למשל: "admin_credit", "transfer"
    amount_slh = Column(Numeric(20, 8), nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
