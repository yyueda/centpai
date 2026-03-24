from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation
import logging

from fastapi import Depends
from app.core.errors import DomainError
from app.features.expenses.dto import (
    ExpenseDTO,
    ExpenseParticipantDTO,
    BalanceDTO,
    SimplifiedDebtDTO,
    SplitRule,
)
from app.features.expenses.algorithms.simplify_debts import simplify_debts
from app.features.expenses.errors import (
    ChatNotFound,
    InvalidAmount,
    NoDebtOwedError,
    NotMember,
    PaymentExceedsBalanceError,
    RecipientNotOwedError,
    ServerError,
    UserNotRegistered,
    ExpenseNotFoundError,
    ExpenseNotOwnedError,
)
from app.features.expenses.repo import ExpensesRepository, get_repo
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("centpai")


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
            logger.error("DB integrity error: %s", e)
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
            logger.error("DB integrity error: %s", e)
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
            (member.user.username if member.user.username else str(member.user.id))
            for member in members
        ]

    # ------------------------------------------------------------------
    # EXPENSES
    # ------------------------------------------------------------------

    async def add_expense(
        self, tg_chat_id: int, tg_user_id: int, amount: Decimal, desc: str
    ) -> list[BalanceDTO]:
        if amount <= 0:
            raise InvalidAmount()

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

            members = await self.repo.list_members(chat.id)
            member_ids = [m.user_id for m in members]

            deltas = self._calc_equal_split_deltas(amount, payer.id, member_ids)
            expense = await self.repo.create_expense(chat.id, payer.id, amount, desc)

            # Deltas return negative amount for those who owe money, thus the minus sign
            userid_to_amount = {
                uid: -delta for uid, delta in deltas.items() if uid != payer.id
            }
            await self.repo.create_splits(expense, userid_to_amount)
            updated_balances = await self.repo.update_balances(chat.id, deltas)
        except IntegrityError as e:
            await self.repo.db.rollback()
            logger.error("DB integrity error: %s", e)
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
        username_amounts: list[str],
        split_rule: SplitRule,
        request_username: str,
    ) -> list[BalanceDTO]:
        if amount <= 0:
            raise InvalidAmount()

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

            usernameToAmount = self._parse_split(
                username_amounts, amount, request_username, split_rule
            )

            userid_to_amount = {}
            for username, amt in usernameToAmount.items():
                member_user = await self.repo.get_user_by_username(username)
                if not member_user:
                    raise UserNotRegistered(
                        message=f"User {username} is not registered yet."
                    )
                is_member = await self.repo.is_member(chat.id, member_user.id)
                if not is_member:
                    raise NotMember(username=username)

                userid_to_amount[member_user.id] = amt

            deltas = self._calc_split_rule_deltas(amount, payer.id, userid_to_amount)

            # Deltas return negative amount for those who owe money, thus the minus sign
            userid_to_amount = {
                uid: -delta for uid, delta in deltas.items() if uid != payer.id
            }
            expense = await self.repo.create_expense(chat.id, payer.id, amount, desc)
            await self.repo.create_splits(expense, userid_to_amount)
            updated_balances = await self.repo.update_balances(chat.id, deltas)

        except IntegrityError as e:
            await self.repo.db.rollback()
            logger.error("DB integrity error: %s", e)
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
            logger.error("DB integrity error: %s", e)
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

    # ------------------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------------------

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

            from_balance = await self.repo.get_user_balance(chat.id, user.id)
            to_balance = await self.repo.get_user_balance(chat.id, to_user.id)

            # Balances are guranteed to be created when user first joins
            assert from_balance is not None
            assert to_balance is not None

            if from_balance.balance >= 0:
                raise NoDebtOwedError()
            if to_balance.balance <= 0:
                raise RecipientNotOwedError(to_username)
            if amount > abs(from_balance.balance):
                raise PaymentExceedsBalanceError(from_balance.balance, amount)

            # create payment
            await self.repo.create_payment(chat.id, user.id, to_user.id, amount)
            # update balance
            await self.repo.update_balance(chat.id, user.id, to_user.id, amount)

        except IntegrityError as e:
            await self.repo.db.rollback()
            logger.error("DB integrity error: %s", e)
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
    def _split_evenly(amount: Decimal, n: int) -> list[Decimal]:
        """Splits amount into n parts that sum exactly to amount.
        Uses ROUND_DOWN for the base share, distributing remainder cents one-by-one.
        """
        base = (amount / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        remainder_cents = int((amount - base * n) * 100)
        return [
            base + Decimal("0.01") if i < remainder_cents else base for i in range(n)
        ]

    @staticmethod
    def _parse_split(
        username_amounts: list[str],
        amount: Decimal,
        request_username: str,
        split_rule: SplitRule,
    ) -> dict[str, Decimal]:
        if split_rule == SplitRule.EQUAL_SELECTED:
            return ExpensesService._equal_split_selected_users(
                username_amounts, amount, request_username
            )
        elif split_rule == SplitRule.PERCENTAGE:
            return ExpensesService._percentage_split(
                username_amounts, amount, request_username
            )
        else:
            return ExpensesService._amount_split(
                username_amounts, amount, request_username
            )

    @staticmethod
    def _equal_split_selected_users(
        username_amounts: list[str], amount: Decimal, request_username: str
    ) -> dict[str, Decimal]:
        usernames = []
        for username_amount in username_amounts:
            parts = username_amount.split("=")
            if len(parts) > 1:
                raise ValueError(
                    "Invalid equal split format. Usage: /expense_add <amount> <desc> @username1 @username2."
                )
            username = parts[0].lstrip("@")
            if username == request_username:
                raise ValueError(
                    "You do not need to include your own username. Usage: /expense_add <amount> <desc> @username1 @username2."
                )
            usernames.append(username)

        # mentioned users first, requester last — extra cents go to mentioned users
        all_users = usernames + [request_username]
        shares = ExpensesService._split_evenly(amount, len(all_users))
        return dict(zip(all_users, shares))

    @staticmethod
    def _percentage_split(
        username_amounts: list[str], amount: Decimal, request_username: str
    ) -> dict[str, Decimal]:
        # First pass: validate formats and collect (username, percentage) pairs
        parsed: list[tuple[str, float]] = []
        total_percentage = 0
        is_request_username_inside = False
        for username_amount in username_amounts:
            parts = username_amount.split("=")
            if len(parts) != 2 or "%" not in parts[1]:
                raise ValueError(
                    "Invalid percentage split format. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%."
                )
            try:
                percentage = float(parts[1].rstrip("%"))
                username = parts[0].lstrip("@")
                parsed.append((username, percentage))
                total_percentage += percentage
                if username == request_username:
                    is_request_username_inside = True
            except (ValueError, InvalidOperation):
                raise ValueError(
                    "Invalid value. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%."
                )

        if total_percentage != 100:
            raise ValueError(
                "Invalid percentage splits. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%."
            )
        if not is_request_username_inside:
            raise ValueError(
                "You need to include your own username. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%."
            )

        # Second pass: compute shares — last user absorbs rounding remainder
        usernameToAmount: dict[str, Decimal] = {}
        running_total = Decimal(0)
        for i, (username, percentage) in enumerate(parsed):
            if i < len(parsed) - 1:
                share = (amount * Decimal(percentage) / Decimal(100)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                share = amount - running_total
            usernameToAmount[username] = share
            running_total += share

        return usernameToAmount

    @staticmethod
    def _amount_split(
        username_amounts: list[str], amount: Decimal, request_username: str
    ) -> dict[str, Decimal]:
        is_request_username_inside = False
        total_amount: Decimal = Decimal(0)
        usernameToAmount: dict[str, Decimal] = {}
        for username_amount in username_amounts:
            username_amount_split = username_amount.split("=")
            if len(username_amount_split) != 2 or username_amount_split[1] == "":
                raise ValueError(
                    "Invalid amount split format. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4."
                )
            try:
                converted_amount = Decimal(username_amount_split[1]).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                total_amount += converted_amount
                username = username_amount_split[0].lstrip("@")
                usernameToAmount[username] = converted_amount
                if request_username == username:
                    is_request_username_inside = True
            except (ValueError, InvalidOperation):
                raise ValueError(
                    "Invalid value. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4."
                )

        if total_amount != amount:
            raise ValueError(
                "Invalid amount splits. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4."
            )

        if not is_request_username_inside:
            raise ValueError(
                "You need to include your own username. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4."
            )

        return usernameToAmount

    @staticmethod
    def _calc_equal_split_deltas(
        amount: Decimal,
        payer_id: int,
        member_ids: list[int],
    ) -> dict[int, Decimal]:
        """
        Returns {user_id: balance_delta} for an equal split.
        Positive = gains (payer), negative = owes (non-payer).
        Extra remainder cents go to non-payers first.
        """
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        n = len(member_ids)
        if n == 0:
            return {payer_id: amount}

        # Non-payers first so they absorb remainder cents; payer gets last share
        non_payers = [uid for uid in member_ids if uid != payer_id]
        ordered = non_payers + [payer_id]
        shares = ExpensesService._split_evenly(amount, n)
        deltas = {uid: -share for uid, share in zip(ordered, shares)}
        deltas[payer_id] += amount
        return deltas

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
            userid: (amount - amt if userid == payer_id else -amt)
            for userid, amt in userid_to_amount.items()
        }
