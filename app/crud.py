from decimal import Decimal
from sqlalchemy.orm import Session

from app import models


def get_or_create_user(db: Session, telegram_id: int, username: str | None):
    """
    מאתר משתמש לפי telegram_id; אם לא קיים – יוצר עם balance_slh=0.
    """
    user = (
        db.query(models.User)
        .filter(models.User.telegram_id == telegram_id)
        .first()
    )
    if not user:
        user = models.User(
            telegram_id=telegram_id,
            username=username,
            balance_slh=Decimal("0"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def set_bnb_address(db: Session, user: models.User, address: str):
    """
    מעדכן את כתובת ה-BNB של המשתמש.
    """
    user.bnb_address = address
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def change_balance(
    db: Session,
    user: models.User,
    delta_slh: float | Decimal,
    tx_type: str,
    from_user: int | None,
    to_user: int | None,
) -> models.Transaction:
    """
    שינוי יתרה פנימית + יצירת טרנזקציה בלג'ר.
    """
    amount = Decimal(str(delta_slh))

    current = user.balance_slh or Decimal("0")
    user.balance_slh = current + amount

    tx = models.Transaction(
        from_user=from_user,
        to_user=to_user,
        amount_slh=amount,
        tx_type=tx_type,
    )

    db.add(user)
    db.add(tx)
    db.commit()
    db.refresh(user)
    db.refresh(tx)
    return tx


def internal_transfer(
    db: Session,
    sender: models.User,
    receiver: models.User,
    amount_slh: float | Decimal,
) -> models.Transaction:
    """
    העברת SLH פנימית בין שני משתמשים (off-chain).
    """
    amount = Decimal(str(amount_slh))

    sender_balance = sender.balance_slh or Decimal("0")
    if sender_balance < amount:
        raise ValueError("Insufficient balance for this transfer.")

    # מורידים מהשולח
    sender.balance_slh = sender_balance - amount

    # מוסיפים למקבל
    receiver_balance = receiver.balance_slh or Decimal("0")
    receiver.balance_slh = receiver_balance + amount

    tx = models.Transaction(
        from_user=sender.telegram_id,
        to_user=receiver.telegram_id,
        amount_slh=amount,
        tx_type="internal_transfer",
    )

    db.add(sender)
    db.add(receiver)
    db.add(tx)
    db.commit()
    db.refresh(sender)
    db.refresh(receiver)
    db.refresh(tx)
    return tx
