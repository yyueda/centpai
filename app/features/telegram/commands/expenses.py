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


def parse_id(id: str) -> int:
    try:
        value = int(id)
        if value <= 0:
            raise ValueError("ID must be positive")
        return value
    except ValueError:
        raise ValueError("Invalid id format")


def parse_user(user: str) -> int:
    user_split = user.split("@")
    if len(user_split) != 2 or user_split[0] != '':
        raise ValueError("Incorrect user format")

    return user_split[1]

async def handleListExpenses(ctx: TgContext, messenger: Messenger, svc: ExpensesService) -> None:
    try:
        expenses = await svc.get_expenses(ctx.tg_chat_id)
        balances = await svc.get_balances(ctx.tg_chat_id)
        if expenses:
            message_lines = ["Recent expenses:"]
            for exp in expenses:
                participants = exp.participants
                message = [f"• Expense ID ({exp.id}), {exp.paid_by} paid {exp.amount} for {exp.desc} on {exp.created_at.strftime('%Y-%m-%d')}"]
                if participants:
                    for participant in participants:
                        message.append(f"• {participant.username} owes {participant.amount_owed}")
                
                message_lines.append("\n".join(message))
            
            message_lines.append("Balances:")
            message = []
            for balance in balances:
                if balance.balance == 0:
                    continue
                message.append(f"• {balance.username} {'owes ' + -balance.balance if balance.balance < 0 else 'is owed ' + balance.balance} in total")
            
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


async def handleRemoveExpense(ctx: TgContext, messenger: Messenger, svc: ExpensesService, args: list[str]) -> None:
    if not args:
        await messenger.send_message(ctx.tg_chat_id, "Usage: /expense_remove <Expense ID>", reply_to_message_id=ctx.message_id)
        return
    
    try:
        expense_id = parse_id(args[0])
        await svc.remove_expense(ctx.tg_chat_id, ctx.tg_user_id, expense_id)

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"Expense ({expense_id}) removed.",
            reply_to_message_id=ctx.message_id
        )
    except ValueError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=str(e),
            reply_to_message_id=ctx.message_id
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id
        )


async def handlePay(ctx: TgContext, messenger: Messenger, svc: ExpensesService, args: list[str]) -> None:
    if not args or len(args) != 2:
        await messenger.send_message(ctx.tg_chat_id, "Usage: /pay @user <amount>", reply_to_message_id=ctx.message_id)
        return
    
    try:
        username = parse_user(args[0])
        amount = parse_amount(args[1])
        await svc.process_payment(ctx.tg_chat_id, ctx.tg_user_id, username, amount)

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{amount} has been paid to {username}.",
            reply_to_message_id=ctx.message_id
        )
    except ValueError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=str(e),
            reply_to_message_id=ctx.message_id
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"{e.message}",
            reply_to_message_id=ctx.message_id
        )