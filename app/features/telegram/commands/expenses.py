from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from app.core.errors import DomainError
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
        print(f"amount is {amount}")
        desc = " ".join(
            args[1 : len(args) - len_mentioned_usernames]
        )  # rest becomes description
        print(f"desc is {desc}")

        if len_mentioned_usernames > 0:
            # check if there is = sign after username, if no then equal split
            usernameToAmount = check_split_rule(
                args[len(args) - len_mentioned_usernames :]
            , amount, ctx.username)
            print(usernameToAmount)
            await svc.add_expense_selected_users(
                ctx.tg_chat_id,
                ctx.tg_user_id,
                amount,
                desc,
                usernameToAmount
            )

        else:
            updated_balances = await svc.add_expense(
                ctx.tg_chat_id, ctx.tg_user_id, amount, desc
            )

            lines = [f"Expense added. Updated balances:"]
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
        raise ValueError("Please input a valid amount. Usage: /expense_add <amount> <desc>.")


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


def check_split_rule(username_amounts: list[str], amount: Decimal, request_username: str) -> dict[str, Decimal]:
    print(f"username_amounts is {username_amounts}")
    username_amount_split = username_amounts[0].split('=')
    print(f"username split is {username_amount_split}")
    if len(username_amount_split) == 1:
        #equal split among selected users
        equal_amount = Decimal(amount / (len(username_amounts) + 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return equal_split_selected_users(username_amounts, equal_amount, request_username)
    elif len(username_amount_split) == 2 and ('%' in username_amount_split[1]):
        #percentage
        return percentage_split(username_amounts, amount, request_username)
    else:
        #amounts
        return amount_split(username_amounts, amount, request_username)


def equal_split_selected_users(username_amounts: list[str], split_amount: Decimal, request_username: str) -> dict[str, Decimal]:

    isRequestUsernameInside = False
    usernameToAmount: dict[str, Decimal] = {}
    for username_amount in username_amounts:
        username_amount_split = username_amount.split('=')
        if len(username_amount_split) > 1:
            raise ValueError("Invalid equal split format. Usage: /expense_add <amount> <desc> @username1 @username2.")
        username = username_amount_split[0].lstrip('@')
        usernameToAmount[username] = split_amount
        if username == request_username:
            isRequestUsernameInside = True
    
    if isRequestUsernameInside:
        raise ValueError("You do not need to include your own username. Usage: /expense_add <amount> <desc> @username1 @username2.")

    usernameToAmount[request_username] = split_amount
    
    return usernameToAmount


def percentage_split(username_amounts: list[str], amount: Decimal, request_username: str) -> dict[str, Decimal]:

    isRequestUsernameInside = False
    total_percentage = 0
    usernameToAmount: dict[str, Decimal] = {}
    for username_amount in username_amounts:
        username_amount_split = username_amount.split('=')
        if len(username_amount_split) != 2 or ('%' not in username_amount_split[1]):
            raise ValueError("Invalid percentage split format. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%.")
        try:
            percentage = float(username_amount_split[1].rstrip('%'))
            total_percentage += percentage
            percentage_amount = Decimal(amount * (Decimal(percentage) / Decimal(100))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            username = username_amount_split[0].lstrip('@')
            usernameToAmount[username] = percentage_amount
            if request_username == username:
                isRequestUsernameInside = True
        except (ValueError, InvalidOperation):
            raise ValueError("Invalid value. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%.")

    if total_percentage != 100:
        raise ValueError("Invalid percentage splits. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%.")
    
    if not isRequestUsernameInside:
        raise ValueError("You need to include your own username. Usage: /expense_add <amount> <desc> @username1=60% @my_username=40%.")

    return usernameToAmount

def amount_split(username_amounts: list[str], amount: Decimal, request_username: str) -> dict[str, Decimal]:
    isRequestUsernameInside = False
    total_amount = 0
    usernameToAmount: dict[str, Decimal] = {}
    for username_amount in username_amounts:
        username_amount_split = username_amount.split('=')
        print(f"amount_split, username split is {username_amount_split}")
        if len(username_amount_split) != 2 or username_amount_split[1] == '':
            raise ValueError("Invalid amount split format. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4.")
        try:
            converted_amount = Decimal(username_amount_split[1]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_amount += converted_amount
            username = username_amount_split[0].lstrip('@')
            usernameToAmount[username] = converted_amount
            if request_username == username:
                isRequestUsernameInside = True
        except (ValueError, InvalidOperation):
            raise ValueError("Invalid value. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4.")

    if total_amount != amount:
        raise ValueError("Invalid amount splits. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4.")

    if not isRequestUsernameInside:
        raise ValueError("You need to include your own username. Usage: /expense_add <amount> <desc> @username1=6 @my_username=4.")

    return usernameToAmount
    

async def handleListExpenses(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    try:
        expenses = await svc.get_expenses(ctx.tg_chat_id)
        balances = await svc.get_balances(ctx.tg_chat_id)
        if expenses:
            message_lines = ["Recent expenses:"]
            for exp in expenses:
                participants = exp.participants
                message = [
                    f"• Expense ID ({exp.id}), {exp.paid_by} paid {exp.amount} for {exp.desc} on {exp.created_at.strftime('%Y-%m-%d')}"
                ]
                if participants:
                    for participant in participants:
                        message.append(
                            f"• {participant.username} owes {participant.amount_owed}"
                        )

                message_lines.append("\n".join(message))

            message_lines.append("Balances:")
            message: list[str] = []
            for balance in balances:
                if balance.balance == 0:
                    continue
                if balance.balance < 0:
                    message.append(
                        f"• {balance.username} owes {-balance.balance} in total"
                    )
                else:
                    message.append(
                        f"• {balance.username} is owed {balance.balance} in total"
                    )

            message_lines.append("\n".join(message))

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
