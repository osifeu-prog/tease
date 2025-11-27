from decimal import Decimal
from sqlalchemy.orm import Session

from app import models


def get_or_create_user(db: Session, telegram_id: int, username: str | None):
    user = db.query(models.User).filter(models.User.telegram_id == telegram_id).first()
    if user:
        # עדכון username אם השתנה
        if username is not None and user.username != username:
            user.username = username
            db.add(user)
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


def set_bnb_address(db: Session, user: models.User, addr: str) -> models.User:
    user.bnb_address = addr
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
    amount = Decimal(str(delta_slh))
    new_balance = (user.balance_slh or Decimal("0")) + amount
    user.balance_slh = new_balance

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
    amount = Decimal(str(amount_slh))

    if amount <= 0:
        raise ValueError("Amount must be positive")

    sender_balance = sender.balance_slh or Decimal("0")
    if sender_balance < amount:
        raise ValueError("Insufficient balance for this transfer.")

    receiver_balance = receiver.balance_slh or Decimal("0")

    sender.balance_slh = sender_balance - amount
    receiver.balance_slh = receiver_balance + amount

    tx = models.Transaction(
        from_user=sender.telegram_id,
        to_user=receiver.telegram_id,
        amount_slh=amount,
        tx_type="transfer",
    )
    db.add(sender)
    db.add(receiver)
    db.add(tx)
    db.commit()
    db.refresh(sender)
    db.refresh(receiver)
    db.refresh(tx)
    return tx
