from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from app.core.errors import DomainError
from app.features.expenses.dto import SplitRule
from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext


async def handleAddExpense(
    ctx: TgContext,
    messenger: Messenger,
    svc: ExpensesService,
    args: list[str],
    mentioned_usernames: list[str],
) -> None:
    if not args:
        await messenger.send_message(
            ctx.tg_chat_id,
            "Usage: /expense_add <amount> <desc>",
            reply_to_message_id=ctx.message_id,
        )
        return

    try:
        len_mentioned_usernames = len(mentioned_usernames)
        amount = parse_amount(args[0])
        desc = " ".join(
            args[1 : len(args) - len_mentioned_usernames]
        )  # rest becomes description

        if len_mentioned_usernames > 0:
            username_amounts = args[len(args) - len_mentioned_usernames :]
            split_rule = check_split_rule(username_amounts)
            updated_balances = await svc.add_expense_selected_users(
                ctx.tg_chat_id,
                ctx.tg_user_id,
                amount,
                desc,
                username_amounts,
                split_rule,
                ctx.username,
            )

        else:
            updated_balances = await svc.add_expense(
                ctx.tg_chat_id, ctx.tg_user_id, amount, desc
            )

        lines = [f"Expense added.\n\nBalances:"]
        for b in updated_balances:
            if b.balance == 0:
                continue
            if b.balance < 0:
                lines.append(f"• {b.username} owes {-b.balance} in total")
            else:
                lines.append(f"• {b.username} is owed {b.balance} in total")

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text="\n".join(lines),
            reply_to_message_id=ctx.message_id,
        )
    except ValueError as e:
        await messenger.send_message(
            ctx.tg_chat_id,
            str(e),
            ctx.message_id,
        )
    except DomainError as e:
        await messenger.send_message(ctx.tg_chat_id, e.message, ctx.message_id)


def parse_amount(amount: str) -> Decimal:
    try:
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError(
            "Please input a valid amount. Usage: /expense_add <amount> <desc>."
        )


def parse_id(id: str) -> int:
    try:
        value = int(id)
        if value <= 0:
            raise ValueError("ID must be positive")
        return value
    except ValueError:
        raise ValueError("Invalid id format")


def parse_user(user: str) -> str:
    user_split = user.split("@")
    if len(user_split) != 2 or user_split[0] != "":
        raise ValueError("Incorrect user format")

    return user_split[1]


def check_split_rule(username_amounts: list[str]) -> SplitRule:
    first_split = username_amounts[0].split("=")
    if len(first_split) == 1:
        return SplitRule.EQUAL_SELECTED
    elif len(first_split) == 2 and "%" in first_split[1]:
        return SplitRule.PERCENTAGE
    else:
        return SplitRule.AMOUNT


async def handleListExpenses(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    try:
        expenses = await svc.get_expenses(ctx.tg_chat_id)
        balances = await svc.get_balances(ctx.tg_chat_id)
        if expenses:
            message_lines = ["Recent Expenses"]
            for exp in expenses:
                participants = exp.participants
                lines = [
                    f"[#{exp.id}] {exp.desc} — ${exp.amount} by {exp.paid_by} ({exp.created_at.strftime('%Y-%m-%d')})"
                ]
                if participants:
                    for participant in participants:
                        lines.append(
                            f"  └ {participant.username} owes ${participant.amount_owed}"
                        )
                message_lines.append("\n".join(lines))

            balance_lines = ["Balances"]
            for balance in balances:
                if balance.balance == 0:
                    continue
                if balance.balance < 0:
                    balance_lines.append(f"{balance.username} -${-balance.balance}")
                else:
                    balance_lines.append(f"{balance.username} +${balance.balance}")

            message_lines.append("\n".join(balance_lines))

            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="\n\n".join(message_lines),
                reply_to_message_id=ctx.message_id,
            )
        else:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="No expenses found.",
                reply_to_message_id=ctx.message_id,
            )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id,
        )


async def handleRemoveExpense(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService, args: list[str]
) -> None:
    if not args:
        await messenger.send_message(
            ctx.tg_chat_id,
            "Usage: /expense_remove <Expense ID>",
            reply_to_message_id=ctx.message_id,
        )
        return

    try:
        expense_id = parse_id(args[0])
        await svc.remove_expense(ctx.tg_chat_id, ctx.tg_user_id, expense_id)

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"Expense ({expense_id}) removed.",
            reply_to_message_id=ctx.message_id,
        )
    except ValueError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id, text=str(e), reply_to_message_id=ctx.message_id
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id,
        )


async def handlePay(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService, args: list[str]
) -> None:
    if not args or len(args) != 2:
        await messenger.send_message(
            ctx.tg_chat_id,
            "Usage: /pay @user <amount>",
            reply_to_message_id=ctx.message_id,
        )
        return

    try:
        username = parse_user(args[0])
        amount = parse_amount(args[1])
        await svc.process_payment(ctx.tg_chat_id, ctx.tg_user_id, username, amount)

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{amount} has been paid to {username}.",
            reply_to_message_id=ctx.message_id,
        )
    except ValueError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id, text=str(e), reply_to_message_id=ctx.message_id
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id,
        )


async def handleDebts(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService, args: list[str]
) -> None:
    try:
        simplified_debts = await svc.get_simplified_debts(ctx.tg_chat_id)

        lines = [f"Simplified Debts:"]
        for d in simplified_debts:
            lines.append(f"• {d.from_user} -> {d.to_user} ${d.amount}")

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text="\n".join(lines),
            reply_to_message_id=ctx.message_id,
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id,
        )
