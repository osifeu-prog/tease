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

    # יתרת SLH "העיקרית" (כמו שהיה עד עכשיו)
    balance_slh = Column(Numeric(24, 6), nullable=False, default=0)

    # --- רפררלים / Sela פנימי ---

    # מי הפנה אותי (telegram_id של המפנה, אם יש)
    referred_by = Column(BigInteger, nullable=True, index=True)

    # יתרת Sela פנימי (תגמולי שיתוף / הפקדות)
    referral_rewards_sela = Column(Numeric(24, 8), nullable=False, default=0)


class Transaction(Base):
    """
    טבלת טרנזקציות פנימיות (Off-Chain Ledger).
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # מזהי טלגרם (לא FK פורמלי, פשוט שמירה של ה-ID)
    from_user = Column(BigInteger, nullable=True)
    to_user = Column(BigInteger, nullable=True)

    amount_slh = Column(Numeric(24, 6), nullable=False)
    tx_type = Column(String(50), nullable=False)


class Referral(Base):
    """
    לוג רפררלים – כל אירוע תגמול (שיתוף / בונוס הפקדה).
    """

    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # מי הפנה (תמיד קיים)
    inviter_telegram_id = Column(BigInteger, nullable=False, index=True)

    # מי הוזמן (אם כבר קיים במערכת)
    invitee_telegram_id = Column(BigInteger, nullable=True, index=True)

    # כמה Sela פנימי קיבל המפנה
    reward_sela = Column(Numeric(24, 8), nullable=False, default=0)

    # סוג האירוע – "share" / "deposit"
    kind = Column(String(50), nullable=False, default="share")

    # הערות חופשיות (ID של עסקה, תיאור הפקדה וכו')
    notes = Column(String(255), nullable=True)
