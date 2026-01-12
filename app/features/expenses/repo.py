from decimal import Decimal
from typing import Iterable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import Depends

from app.db.database import get_session
from app.features.expenses.models import Balance, Chat, ChatMember, Expense, ExpenseSplit, Payment, User


def get_repo(session: AsyncSession = Depends(get_session)) -> "ExpensesRepository":
        return ExpensesRepository(session)


class ExpensesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ------------------------------------------------------------------
    # CHATS
    # ------------------------------------------------------------------

    async def get_chat_by_tg_id(self, tg_chat_id: int) -> Chat | None:
        stmt = select(Chat).where(Chat.telegram_chat_id == tg_chat_id)
        return await self.db.scalar(stmt)

    async def get_or_create_chat(self, tg_chat_id: int) -> Chat:
        chat = await self.get_chat_by_tg_id(tg_chat_id)
        if chat:
            return chat

        chat = Chat(telegram_chat_id=tg_chat_id)
        self.db.add(chat)

        try:
            await self.db.flush()
            return chat
        except IntegrityError:
           # another concurrent request inserted first
            chat = await self.get_chat_by_tg_id(tg_chat_id)
            if not chat:
                raise
            return chat
        
    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------

    async def get_user_by_tg_id(self, tg_user_id: int) -> User | None:
        stmt = select(User).where(User.telegram_user_id == tg_user_id)
        return await self.db.scalar(stmt)

    async def get_or_create_user(
        self,
        tg_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        user = await self.get_user_by_tg_id(tg_user_id)
        if user:
            return user

        user = User(
            telegram_user_id=tg_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.db.add(user)

        try:
            await self.db.flush() # assigns user.id
            return user
        except IntegrityError:
            user = await self.get_user_by_tg_id(tg_user_id)
            if not user:
                raise
            return user
    
    # ------------------------------------------------------------------
    # MEMBERS (ChatMember join table)
    # ------------------------------------------------------------------

    async def add_member(self, chat_id: int, user_id: int) -> None:
        from sqlalchemy.dialects.postgresql import insert
        stmt = (
            insert(ChatMember)
            .values(chat_id=chat_id, user_id=user_id)
            .on_conflict_do_nothing(
                index_elements=[ChatMember.chat_id, ChatMember.user_id]
            )
        )
        await self.db.execute(stmt)
        # self.db.add(ChatMember(chat_id=chat_id, user_id=user_id))
        # await self.db.flush()

    async def remove_member(self, chat_id: int, tg_user_id: int) -> bool:
        stmt = select(User).where(
            User.telegram_user_id == tg_user_id,
        )
        user = await self.db.scalar(stmt)
        if user is None:
            return False

        stmt = select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user.id,
        )
        member = await self.db.scalar(stmt)

        if member is None:
            return False

        await self.db.delete(member)
        await self.db.flush()

        return True

    async def list_members(self, chat_id: int) -> list[ChatMember]:
        stmt = (
            select(ChatMember)
            .where(ChatMember.chat_id == chat_id)
            .options(selectinload(ChatMember.user))
            .order_by(ChatMember.id.asc())
        )
        members = (await self.db.scalars(stmt)).all()
        return list(members)

    async def is_member(self, chat_id: int, user_id: int) -> bool:
        stmt = (
            select(ChatMember.id)
            .where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
            .limit(1)
        )
        return (await self.db.scalar(stmt)) is not None

    # ------------------------------------------------------------------
    # EXPENSES
    # ------------------------------------------------------------------

    async def create_expense(
        self, 
        chat_id: int, 
        user_id: int, 
        amount: Decimal, 
        description: str
    ) -> None:
        self.db.add(Expense(
            chat_id=chat_id,
            payer_id=user_id,
            amount=amount,
            description=description
        ))
        await self.db.flush()  # assigns expense.id

    async def add_splits(self, splits: Iterable[ExpenseSplit]) -> None:
        self.db.add_all(splits)
        await self.db.flush()

    async def list_expenses(self, chat_id: int, limit: int = 50) -> list[Expense]:
        stmt = (
            select(Expense)
            .where(Expense.chat_id == chat_id)
            .options(
                selectinload(Expense.splits),      # loads splits for balance calc
                selectinload(Expense.payer),       # optional: payer details
            )
            .order_by(Expense.created_at.desc())
            .limit(limit)
        )
        res = (await self.db.scalars(stmt)).all()
        return list(res)

    # ------------------------------------------------------------------
    # PAYMENTS
    # ------------------------------------------------------------------

    async def create_payment(self, payment: Payment) -> None:
        self.db.add(payment)
        await self.db.flush()


    async def list_payments(self, chat_id: int, limit: int = 100) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.chat_id == chat_id)
            .options(
                selectinload(Payment.from_user),
                selectinload(Payment.to_user),
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        res = (await self.db.scalars(stmt)).all()
        return list(res)

    # ------------------------------------------------------------------
    # BALANCES
    # ------------------------------------------------------------------

    async def get_user_balance(self, chat_id: int, user_id: int) -> Balance | None:
        stmt = select(Balance).where(Balance.chat_id == chat_id, Balance.user_id == user_id)
        return await self.db.scalar(stmt)
    
    async def create_balance(self, chat_id: int, user_id: int) -> None:
        bal = await self.get_user_balance(chat_id, user_id)
        if bal:
            return
        
        bal = Balance(chat_id=chat_id, user_id=user_id, balance=Decimal("0.00"))
        self.db.add(bal)
        await self.db.flush()

        return

    async def list_balances(self, chat_id: int) -> list[Balance]:
        stmt = (
            select(Balance)
            .where(Balance.chat_id == chat_id)
            .options(
                selectinload(Balance.chat),
                selectinload(Balance.user),
            )
            .order_by(Balance.updated_at.desc())
        )
        res = (await self.db.scalars(stmt)).all()
        return list(res)
    