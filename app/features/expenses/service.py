from decimal import Decimal

from fastapi import Depends
from app.core.errors import DomainError
from app.features.expenses.dto import ExpenseDTO, ExpenseParticipantDTO, BalanceDTO
from app.features.expenses.errors import ChatNotFound, NotMember, ServerError, UserNotRegistered, ExpenseNotFoundError, ExpenseNotOwnedError, NoDebtOwedError, PaymentExceedsDebtError
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
    

    async def remove_member(
            self,
            tg_chat_id: int,
            tg_user_id: int
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
            
            await self.repo.remove_member(chat.id, tg_user_id)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e  
        except DomainError:
            await self.repo.db.rollback()
            raise 
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


    async def get_members(self, tg_chat_id: int) -> list[str]:
        chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
        if not chat:
            raise ChatNotFound()
        
        members = await self.repo.list_members(chat.id)
        return [
            member.user.username if member.user.username else str(member.user.id)  # TODO: we should make username nullable=False
            for member in members
        ]

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
            
            # TODO: Create splits + update balance in repo
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
                id=expense.id,
                paid_by=expense.payer.username,
                amount=expense.amount,
                desc=expense.description,
                created_at=expense.created_at,
                participants=[
                    ExpenseParticipantDTO(
                        username=split.user.username,
                        amount_owed=split.amount
                    )
                    for split in expense.splits
                ]

        ) for expense in expenses_list]


    async def remove_expense(self, tg_chat_id: int, tg_user_id: int, expense_id: int) -> None:
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
            
            expense = await self.repo.get_expense(chat.id, expense_id)
            if expense is None:
                raise ExpenseNotFoundError(expense_id)

            if expense.payer_id != user.id:
                raise ExpenseNotOwnedError(expense_id, user.username)

            await self.repo.remove_expense(expense)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e  
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()


    # ------------------------------------------------------------------
    # BALANCES
    # --------------------------------------------------------------------
    
    async def get_balances(self, tg_chat_id: int) -> list[BalanceDTO]:
        chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
        if not chat:
            raise ChatNotFound()
        
        balances = await self.repo.list_balances(chat.id)

        return [
            BalanceDTO(
                username=balance.user.username,
                balance=balance.balance
            ) for balance in balances]
    

    async def process_payment(self, tg_chat_id: int, tg_user_id: int, to_username: str, amount: Decimal) -> None:
        await self.repo.db.begin()

        try:
            user = await self.repo.get_user_by_tg_id(tg_user_id)
            if not user:
                raise UserNotRegistered()
            
            to_user = await self.repo.get_user_by_username(to_username)
            if not to_user:
                raise UserNotRegistered(message="User {to_username} is not registered yet.")

            chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
            if not chat:
                raise ChatNotFound()
            
            is_member = await self.repo.is_member(chat.id, user.id)
            if not is_member:
                raise NotMember()
            
            to_user_is_member = await self.repo.is_member(chat.id, to_user.id)
            if not to_user_is_member:
                raise NotMember(username=to_username)
            
            total_amount_still_owed = await self.repo.get_pairwise_debt(chat.id, user.id, to_user.id)
            if total_amount_still_owed == 0:
                raise NoDebtOwedError(to_username)
            elif amount > total_amount_still_owed:
                raise PaymentExceedsDebtError(total_amount_still_owed, amount, to_username)
            
            #create payment
            await self.repo.create_payment(chat.id, user.id, to_user.id, amount)
            #update balance
            await self.repo.update_balance(chat.id, user.id, to_user.id, amount)

        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e  
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()