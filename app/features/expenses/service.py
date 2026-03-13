from decimal import ROUND_HALF_UP, Decimal

from fastapi import Depends
from app.core.errors import DomainError
from app.features.expenses.dto import (
    ExpenseDTO,
    ExpenseParticipantDTO,
    BalanceDTO,
    SimplifiedDebtDTO,
)
from app.features.expenses.algorithms.simplify_debts import simplify_debts
from app.features.expenses.errors import (
    ChatNotFound,
    NotMember,
    ServerError,
    UserNotRegistered,
    ExpenseNotFoundError,
    ExpenseNotOwnedError,
    NoDebtOwedError,
    PaymentExceedsDebtError,
)
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
    async def add_member(self, tg_chat_id: int, tg_user_id: int, **user_fields) -> None:
        await self.repo.db.begin()

        try:
            await self._ensure_member_and_balance(tg_chat_id, tg_user_id, **user_fields)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e
        else:
            await self.repo.db.commit()

    async def remove_member(self, tg_chat_id: int, tg_user_id: int) -> None:
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
        self, tg_chat_id: int, tg_user_id: int, **user_fields
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
            (
                member.user.username if member.user.username else str(member.user.id)
            )
            for member in members
        ]

    # ------------------------------------------------------------------
    # EXPENSES
    # ------------------------------------------------------------------

    async def add_expense(
        self, tg_chat_id: int, tg_user_id: int, amount: Decimal, desc: str
    ) -> list[BalanceDTO]:
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

            members = await self.repo.list_members(chat.id)
            member_ids = [m.user_id for m in members]

            deltas = self._calc_equal_split_deltas(amount, user.id, member_ids)

            await self.repo.create_expense(chat.id, user.id, amount, desc)
            updated_balances = await self.repo.update_balances(chat.id, deltas)
        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()
        
        return [
            BalanceDTO(username=b.user.username, balance=b.balance)
            for b in updated_balances
        ]
    

    async def add_expense_selected_users(
        self,
        tg_chat_id: int, 
        tg_user_id: int,
        amount: Decimal,
        desc: str,
        usernameToAmount: dict[str, Decimal]
    ) -> list[BalanceDTO]:
        await self.repo.db.begin()

        try:
            payer = await self.repo.get_user_by_tg_id(tg_user_id)
            if not payer:
                raise UserNotRegistered()

            chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
            if not chat:
                raise ChatNotFound()

            is_member = await self.repo.is_member(chat.id, payer.id)
            if not is_member:
                raise NotMember()

            userid_to_amount = {}
            for username, amt in usernameToAmount.items():
                member_user = await self.repo.get_user_by_username(username)
                if not member_user:
                    raise UserNotRegistered(message=f"User {username} is not registered yet.")
                is_member = await self.repo.is_member(chat.id, member_user.id)
                if not is_member:
                    raise NotMember(username=username)

                userid_to_amount[member_user.id] = amt

            deltas = self._calc_split_rule_deltas(amount, payer.id, userid_to_amount)
            await self.repo.create_expense(chat.id, payer.id, amount, desc, userid_to_amount)
            updated_balances = await self.repo.update_balances(chat.id, deltas)

        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e  
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()
        
        return [
            BalanceDTO(username=b.user.username, balance=b.balance)
            for b in updated_balances
        ]

    
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
                        username=split.user.username, amount_owed=split.amount
                    )
                    for split in expense.splits
                ],
            )
            for expense in expenses_list
        ]

    async def remove_expense(
        self, tg_chat_id: int, tg_user_id: int, expense_id: int
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
            BalanceDTO(username=balance.user.username, balance=balance.balance)
            for balance in balances
        ]

    async def get_simplified_debts(self, tg_chat_id: int) -> list[SimplifiedDebtDTO]:
        chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
        if not chat:
            raise ChatNotFound()

        balances = await self.repo.list_balances(chat.id)
        balance_pairs = [(b.user.username, b.balance) for b in balances]

        payments = simplify_debts(balance_pairs)

        return [
            SimplifiedDebtDTO(from_user=f, to_user=t, amount=a) for f, t, a in payments
        ]

    async def process_payment(
        self, tg_chat_id: int, tg_user_id: int, to_username: str, amount: Decimal
    ) -> None:
        await self.repo.db.begin()

        try:
            user = await self.repo.get_user_by_tg_id(tg_user_id)
            if not user:
                raise UserNotRegistered()

            to_user = await self.repo.get_user_by_username(to_username)
            if not to_user:
                raise UserNotRegistered(
                    message="User {to_username} is not registered yet."
                )

            chat = await self.repo.get_chat_by_tg_id(tg_chat_id)
            if not chat:
                raise ChatNotFound()

            is_member = await self.repo.is_member(chat.id, user.id)
            if not is_member:
                raise NotMember()

            to_user_is_member = await self.repo.is_member(chat.id, to_user.id)
            if not to_user_is_member:
                raise NotMember(username=to_username)

            total_amount_still_owed = await self.repo.get_pairwise_debt(
                chat.id, user.id, to_user.id
            )
            if total_amount_still_owed == 0:
                raise NoDebtOwedError(to_username)
            elif amount > total_amount_still_owed:
                raise PaymentExceedsDebtError(
                    total_amount_still_owed, amount, to_username
                )

            # create payment
            await self.repo.create_payment(chat.id, user.id, to_user.id, amount)
            # update balance
            await self.repo.update_balance(chat.id, user.id, to_user.id, amount)

        except IntegrityError as e:
            await self.repo.db.rollback()
            raise ServerError() from e
        except DomainError:
            await self.repo.db.rollback()
            raise
        else:
            await self.repo.db.commit()

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_equal_split_deltas(
        amount: Decimal,
        payer_id: int,
        member_ids: list[int],
    ) -> dict[int, Decimal]:
        """
        Returns {user_id: balance_delta} for an equal split.
        Positive = gains (payer), negative = owes (non-payer).
        """
        n = len(member_ids)
        split_amount = Decimal(amount / n).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return {
            uid: (amount - split_amount if uid == payer_id else -split_amount)
            for uid in member_ids
        }
    
    @staticmethod
    def _calc_split_rule_deltas(
        amount: Decimal,
        payer_id: int,
        userid_to_amount: dict[int, Decimal],
    ) -> dict[int, Decimal]:
        """
        Returns {user_id: balance_delta} for an equal split.
        Positive = gains (payer), negative = owes (non-payer).
        """
        return {
            userid: (amount-amt if userid == payer_id else -amt)
            for userid, amt in userid_to_amount.items()
        }
