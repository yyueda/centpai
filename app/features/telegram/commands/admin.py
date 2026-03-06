from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext

COMMANDS_TEXT = (
    "📋 Commands\n"
    "────────────────────\n\n"
    "👥 Administrative\n"
    "/help — show this help message\n"
    "/join — register yourself in this group\n"
    "/leave — leave the current group\n"
    "/members — list members in this chat\n"
    "/add @user — add a member\n"
    "/remove @user — remove a member\n"
    "/home — view group status and net balances\n\n"
    "💰 Expenses\n"
    "/expense_view — view all expenses breakdown\n"
    "/expense_add <Category> <Amount> [split rule] — add an expense\n"
    "  Example: /expense_add Dinner 48.50\n\n"
    "/expense_remove <Expense ID> — remove an expense by ID\n\n"
    "/pay @user <amount> — record a payment you made to a user\n"
    "  Example: /pay @John 25\n\n"
    "🔀 Split Rules (optional)\n"
    "If omitted, expense is split equally among everyone.\n\n"
    "• Equal split (default):\n"
    "  /expense_add Dinner 48.50\n\n"
    "• Equal split among selected users:\n"
    "  @John @Ben @Calvin @Dylan\n\n"
    "• Exact amounts (Include your own username):\n"
    "  @John=10 @Ben=20 @Dylan=18.5\n\n"
    "• Percentages (Include your own username):\n"
    "  @John=50% @Ben=50%\n\n"
)


async def handleHelp(ctx: TgContext, messenger: Messenger) -> None:
    await messenger.send_message(ctx.tg_chat_id, COMMANDS_TEXT)


async def handleInit(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    await svc.add_member(
        ctx.tg_chat_id,
        ctx.tg_user_id,
        username=ctx.username,
        first_name=ctx.first_name,
        last_name=ctx.last_name,
    )
    await _send_welcome_message(ctx.tg_chat_id, messenger)


async def _send_welcome_message(chat_id: int, messenger: Messenger):
    text = (
        "Welcome to Centpai!\n\n"
        "Tap a button below or enter a command to get started:\n\n" + COMMANDS_TEXT
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "Join Group", "callback_data": "join_group"}],
            [{"text": "Leave Group", "callback_data": "leave_group"}],
            [
                {
                    "text": "View Expenses Breakdown",
                    "callback_data": "view_expenses_breakdown",
                }
            ],
            [{"text": "Help", "callback_data": "help"}],
        ]
    }

    await messenger.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
