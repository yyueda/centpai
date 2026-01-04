from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    members: Mapped[list["ChatMember"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    balances: Mapped[list["Balance"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    chats: Mapped[list["ChatMember"]] = relationship(back_populates="user")
    paid_expenses: Mapped[list["Expense"]] = relationship(back_populates="payer")
    owed_splits: Mapped[list["ExpenseSplit"]] = relationship(back_populates="user")
    sent_payments: Mapped[list["Payment"]] = relationship(
        back_populates="from_user", foreign_keys="Payment.from_user_id"
    )
    received_payments: Mapped[list["Payment"]] = relationship(
        back_populates="to_user", foreign_keys="Payment.to_user_id"
    )
    balances: Mapped[list["Balance"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class ChatMember(Base):
    """
    Join table: which users are part of which Telegram chat
    """
    __tablename__ = "chat_members"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    chat: Mapped["Chat"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="chats")


class Expense(Base):
    __tablename__ = "expenses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), index=True)
    payer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
 
    chat: Mapped["Chat"] = relationship(back_populates="expenses")
    payer: Mapped["User"] = relationship(back_populates="paid_expenses")
    splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan"
    )

class ExpenseSplit(Base):
    """
    How much a user owes from an expense
    Sum(splits.amount) should equal Expense.amount
    """
    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "user_id", name="uq_expense_split_user"),
        CheckConstraint("amount >= 0", name="ck_split_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    expense: Mapped["Expense"] = relationship(back_populates="splits")
    user: Mapped["User"] = relationship(back_populates="owed_splits")


class Payment(Base):
    """
    from_user paid to_user
    """
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        CheckConstraint("from_user_id != to_user_id", name="ck_payment_not_to_self"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)

    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    chat: Mapped["Chat"] = relationship(back_populates="payments")
    from_user: Mapped["User"] = relationship(
        back_populates="sent_payments", foreign_keys=[from_user_id]
    )
    to_user: Mapped["User"] = relationship(
        back_populates="received_payments", foreign_keys=[to_user_id]
    )

class Balance(Base):
    """
    Net balance per user per chat
    """
    __tablename__ = "balances"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_balance"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), ondelete="CASCADE", index=True)

    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chat: Mapped["Chat"] = relationship(back_populates="balances")
    user: Mapped["User"] = relationship(back_populates="balances")
