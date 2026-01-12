from decimal import Decimal

from fastapi import Depends
from app.core.errors import DomainError
from app.features.expenses.dto import ExpenseDTO
from app.features.expenses.errors import ChatNotFound, NotMember, ServerError, UserNotRegistered
from app.features.expenses.repo import ExpensesRepository, get_repo
from sqlalchemy.exc import IntegrityError

def get_service(repo: "ExpensesRepository" = Depends(get_repo)) -> "ExpensesService":
    return ExpensesService(repo)

class ExpensesService:
    def __init__(self, repo: ExpensesRepository):
        self.repo = repo

    # ------------------------------------------------------------------
    # MEMBERSHIP/INIT
    # ------------------------------------------------------------------

    # Executed when bot is first added: initialise new data in db
    async def add_member(
        self, 
        tg_chat_id: int, 
        tg_user_id: int, 
        **user_fields
    ) -> None:
        await self.repo.db.begin()

        try:
            await self._ensure_member_and_balance(tg_chat_id, tg_user_id, **user_fields)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e
        else:
            await self.repo.db.commit()

    async def _ensure_member_and_balance(
        self, 
        tg_chat_id: int, 
        tg_user_id: int, 
        **user_fields
    ) -> None:
        chat = await self.repo.get_or_create_chat(tg_chat_id)
        user = await self.repo.get_or_create_user(tg_user_id, **user_fields)
        await self.repo.add_member(chat.id, user.id)
        await self.repo.create_balance(chat.id, user.id)

    # ------------------------------------------------------------------
    # EXPENSES
    # ------------------------------------------------------------------

    async def add_expense(
        self,
        tg_chat_id: int, 
        tg_user_id: int,
        amount: Decimal,
        desc: str
    ) -> None:
        await self.repo.db.begin()

        try:
            user = await self.repo.get_user_by_tg_id(tg_user_id)
            if not user:
                raise UserNotRegistered()
            
            chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
            if not chat:
                raise ChatNotFound()
            
            is_member = await self.repo.is_member(chat.id, user.id)
            if not is_member:
                raise NotMember()
            
            # TODO: Create splits + update balance
            await self.repo.create_expense(chat.id, user.id, amount, desc)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e  
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()
    
    async def get_expenses(self, tg_chat_id: int) -> list[ExpenseDTO]:
        chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
        if not chat:
            raise ChatNotFound()
        
        # Get last 10 expenses
        expenses_list = await self.repo.list_expenses(chat.id, 10)

        return [
            ExpenseDTO(
                paid_by=(
                    expense.payer.username
                    if expense.payer.username
                    else expense.payer.first_name
                ),
                amount=expense.amount,
                desc=expense.description,
                created_at=expense.created_at

        ) for expense in expenses_list]
