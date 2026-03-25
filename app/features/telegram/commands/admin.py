from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext

COMMANDS_TEXT = (
    "📋 <b>Commands</b>\n\n"
    "👥 <b>Administrative</b>\n"
    "/help — show this help message\n"
    "/join — register yourself in this group\n"
    "/leave — leave the current group\n"
    "/members — list members in this chat\n"
    "/add @user — add a member\n"
    "/remove @user — remove a member\n\n"
    "💰 <b>Expenses</b>\n"
    "/expense_view — view all expenses breakdown\n\n"
    "/expense_add <code>&lt;Category&gt; &lt;Amount&gt; [split rule]</code> — add an expense\n"
    "<i>Example:</i> <code>/expense_add Dinner 48.50</code>\n\n"
    "/expense_remove <code>&lt;Expense ID&gt;</code> — remove an expense by ID\n\n"
    "/pay <code>@user &lt;amount&gt;</code> — record a payment you made to a user\n"
    "<i>Example:</i> <code>/pay @John 25</code>\n\n"
    "/debts — show simplified debts (who owes whom and how much)\n\n"
    "🔀 <b>Split Rules</b> <i>(optional)</i>\n"
    "If omitted, expense is split equally among everyone.\n\n"
    "• <b>Equal split</b> (default):\n"
    "<code>/expense_add Dinner 48.50</code>\n\n"
    "• <b>Equal split among selected users:</b>\n"
    "<code>@John @Ben @Calvin @Dylan</code>\n\n"
    "• <b>Exact amounts</b> (include your own username):\n"
    "<code>@John=10 @Ben=20 @Dylan=18.5</code>\n\n"
    "• <b>Percentages</b> (include your own username):\n"
    "<code>@John=50% @Ben=50%</code>\n\n"
    "────────────────────\n"
    "🚀 <b>Project Status</b>\n"
    "This project is in active development. New features are being added continuously, and we welcome contributions from the community. If you have any suggestions or feature requests, please feel free to open an issue on GitHub.\n\n"
    "🌐 <b>Github:</b> https://github.com/yyueda/centpai"
)


async def handleHelp(ctx: TgContext, messenger: Messenger) -> None:
    await messenger.send_message(ctx.tg_chat_id, COMMANDS_TEXT, parse_mode="HTML")


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
        "<b>Welcome to Centpai!</b>\n\n"
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

    await messenger.send_message(
        chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML"
    )
