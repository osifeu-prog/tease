from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import User, Transaction, ReferralLink, ReferralReward


# =====================
#  Users / Wallet base
# =====================

def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: str | None,
) -> User:
    """
    מחזיר אובייקט User – ואם אין, יוצר אחד חדש.
    """
    user = (
        db.query(User)
        .filter(User.telegram_id == telegram_id)
        .first()
    )

    if user:
        # עדכון username אם השתנה
        if username and user.username != username:
            user.username = username
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(
        telegram_id=telegram_id,
        username=username,
        balance_slh=Decimal("0"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_bnb_address(db: Session, user: User, address: str) -> User:
    """
    עדכון כתובת BNB למשתמש.
    """
    user.bnb_address = address
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# =====================
#  SLH Ledger (Off-Chain)
# =====================

def change_balance(
    db: Session,
    user: User,
    delta_slh: float | Decimal,
    tx_type: str,
    from_user: int | None,
    to_user: int | None,
    note: str | None = None,
) -> Transaction:
    """
    שינוי יתרת SLH למשתמש + יצירת רשומת Transaction.
    """
    # מוודא Decimal
    if not isinstance(delta_slh, Decimal):
        delta_slh = Decimal(str(delta_slh))

    user.balance_slh = (user.balance_slh or Decimal("0")) + delta_slh
    db.add(user)

    tx = Transaction(
        tx_type=tx_type,
        from_user=from_user,
        to_user=to_user,
        amount_slh=delta_slh,
        note=note,
    )
    db.add(tx)
    db.commit()
    db.refresh(user)
    db.refresh(tx)
    return tx


def internal_transfer(
    db: Session,
    sender: User,
    receiver: User,
    amount_slh: float | Decimal,
) -> Transaction:
    """
    העברה פנימית בין שני משתמשים (Off-Chain Ledger).
    """
    if not isinstance(amount_slh, Decimal):
        amount_slh = Decimal(str(amount_slh))

    if amount_slh <= 0:
        raise ValueError("Transfer amount must be positive")

    sender_balance = sender.balance_slh or Decimal("0")
    if sender_balance < amount_slh:
        raise ValueError("Insufficient balance")

    # מחסרים מהשולח
    sender.balance_slh = sender_balance - amount_slh
    db.add(sender)

    # מוסיפים לנמען
    receiver.balance_slh = (receiver.balance_slh or Decimal("0")) + amount_slh
    db.add(receiver)

    tx = Transaction(
        tx_type="internal_transfer",
        from_user=sender.telegram_id,
        to_user=receiver.telegram_id,
        amount_slh=amount_slh,
    )
    db.add(tx)
    db.commit()
    db.refresh(sender)
    db.refresh(receiver)
    db.refresh(tx)
    return tx


# =========================
#  Referrals + SELA Engine
# =========================

def get_or_create_referral_link(
    db: Session,
    user: User,
) -> ReferralLink:
    """
    מחזיר ReferralLink עבור המשתמש.
    אם אין, יוצר קוד בסיסי ref_<telegram_id>.
    """
    existing = (
        db.query(ReferralLink)
        .filter(ReferralLink.owner_telegram_id == user.telegram_id)
        .first()
    )
    if existing:
        return existing

    code = f"ref_{user.telegram_id}"

    link = ReferralLink(
        owner_telegram_id=user.telegram_id,
        code=code,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def record_referral_reward(
    db: Session,
    telegram_id: int,
    delta_sela: float | Decimal,
    reason: str,
    meta: str | None = None,
) -> ReferralReward:
    """
    יוצר רשומת ReferralReward (לוג SELA פנימי).
    לא נוגע עדיין בשום 'balance' – החישוב נעשה בצורה אגרגטיבית.
    """
    if not isinstance(delta_sela, Decimal):
        delta_sela = Decimal(str(delta_sela))

    reward = ReferralReward(
        telegram_id=telegram_id,
        delta_sela=delta_sela,
        reason=reason,
        meta=meta,
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


def get_sela_balance(db: Session, telegram_id: int) -> Decimal:
    """
    מחשב יתרה מצטברת של SELA לפי סכום delta_sela.
    """
    total = (
        db.query(func.coalesce(func.sum(ReferralReward.delta_sela), 0))
        .filter(ReferralReward.telegram_id == telegram_id)
        .scalar()
    )
    if not isinstance(total, Decimal):
        total = Decimal(str(total))
    return total


def get_sela_history(
    db: Session,
    telegram_id: int,
    limit: int = 20,
) -> list[ReferralReward]:
    """
    מחזיר היסטוריית פרסים (SELA) לפי משתמש.
    """
    q = (
        db.query(ReferralReward)
        .filter(ReferralReward.telegram_id == telegram_id)
        .order_by(ReferralReward.created_at.desc())
        .limit(limit)
    )
    return q.all()
