from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from app.core.errors import DomainError
from app.features.expenses.errors import ServerError, ChatNotFound
from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext


async def handleAddExpense(
    ctx: TgContext, 
    messenger: Messenger, 
    svc: ExpensesService,
    args: list[str]
) -> None:
    if not args:
        await messenger.send_message(ctx.tg_chat_id, "Usage: /expense_add <amount> <desc>", reply_to_message_id=ctx.message_id)
        return
    
    try:
        amount = parse_amount(args[0])
        desc = " ".join(args[1:])  # rest becomes description

        await svc.add_expense(
            ctx.tg_chat_id,
            ctx.tg_user_id,
            amount,
            desc
        )

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text="Expense added.",
            reply_to_message_id=ctx.message_id
        )
    except ValueError:
        await messenger.send_message(
            ctx.tg_chat_id,
            "Please input a valid amount. Usage: /expense_add <amount> <desc>.",
            ctx.message_id
        )
    except DomainError as e:
        await messenger.send_message(
            ctx.tg_chat_id,
            e.message,
            ctx.message_id
        )

def parse_amount(amount: str) -> Decimal:
    try:
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError("Invalid amount format")


async def handleListExpenses(ctx: TgContext, messenger: Messenger, svc: ExpensesService) -> None:
    try:
        expenses = await svc.get_expenses(ctx.tg_chat_id)
        if expenses:
            message_lines = ["Recent expenses:"]
            for exp in expenses:
                participants = exp.participants
                message = [f"• {exp.paid_by} paid {exp.amount} for {exp.desc} on {exp.created_at.strftime('%Y-%m-%d')}"]
                if participants:
                    for participant in participants:
                        message.append(f"• {participant.username} owes {participant.amount_owed}")
                
                message_lines.append("\n".join(message))

            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="\n\n".join(message_lines),
                reply_to_message_id=ctx.message_id
            )
        else:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="No expenses found.",
                reply_to_message_id=ctx.message_id
            )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id
        )
