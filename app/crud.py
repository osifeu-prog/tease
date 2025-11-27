from decimal import Decimal
from sqlalchemy.orm import Session

from app import models


def get_or_create_user(db: Session, telegram_id: int, username: str | None):
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if user:
        # עדכון יוזרניימ אם השתנה
        if username and user.username != username:
            user.username = username
            db.commit()
            db.refresh(user)
        return user

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
    user.bnb_address = address
    db.commit()
    db.refresh(user)
    return user


def change_balance(
    db: Session,
    user: models.User,
    delta_slh: float | Decimal,
    tx_type: str,
    from_user: models.User | None,
    to_user: int | None,
) -> models.Transaction:
    delta = Decimal(str(delta_slh))
    user.balance_slh = (user.balance_slh or Decimal("0")) + delta

    tx = models.Transaction(
        from_user_id=getattr(from_user, "id", None),
        to_user_id=user.id if hasattr(user, "id") else to_user,
        tx_type=tx_type,
        amount_slh=delta,
    )
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
    amount = Decimal(str(amount_slh))
    sender_balance = sender.balance_slh or Decimal("0")
    if sender_balance < amount:
        raise ValueError("Insufficient balance")

    sender.balance_slh = sender_balance - amount
    receiver.balance_slh = (receiver.balance_slh or Decimal("0")) + amount

    tx = models.Transaction(
        from_user_id=sender.id,
        to_user_id=receiver.id,
        tx_type="transfer",
        amount_slh=amount,
    )
    db.add(tx)
    db.commit()
    db.refresh(sender)
    db.refresh(receiver)
    db.refresh(tx)
    return tx
