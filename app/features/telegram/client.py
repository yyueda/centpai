import httpx
import logging
from typing import Any, Dict, List, Optional
import collections
import uuid

logger = logging.getLogger("telegram")

BASE = "https://api.telegram.org"

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

    "• Exact amounts:\n"
    "  @John=10 @Ben=20 @Dylan=18.5\n\n"

    "• Percentages:\n"
    "  @John=50% @Ben=50%\n\n"

    "• Shares:\n"
    "  @John=2 @Ben=1 @Dylan=1\n"
)

class TelegramAPI:
    def __init__(self, token: str, timeout: float = 10.0):
        self.base = f"{BASE}/bot{token}"
        self._client = httpx.AsyncClient(base_url=self.base, timeout=timeout)
        self.group = collections.defaultdict(set)
        self.expenses = collections.defaultdict(dict)
        self.commands = [
            {"command": "help", "description": "Show help and examples"},
            {"command": "join", "description": "Join this group"},
            {"command": "leave", "description": "Leave the group"},
            {"command": "expense_add", "description": "Add an expense"},
            {"command": "expense_view", "description": "View all expenses"},
        ]
    
    async def aclose(self) -> None:
        """Close the underlying HTTP client (e.g. on shutdown)."""
        await self._client.aclose()
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_to_message_id: int | None = None,
        reply_markup: dict | None=None,
        parse_mode: str | None=None
    ) -> Dict[str, Any]:
        
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode: payload["parse_mode"] = parse_mode
        if reply_to_message_id: 
            payload["reply_parameters"] = {"message_id": reply_to_message_id}
        
        try:
            r = await self._client.post(f"/sendMessage", json=payload)
            r.raise_for_status()
            
            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(f"Telegram API error: send message failed, {data.get('description')}")
            
            return data
        except Exception as e:
            logger.exception(f"Failed to send Telegram message: {e}")
            raise

    # A secret token to be sent in a header “X-Telegram-Bot-Api-Secret-Token” in every webhook request, 1-256 characters. Only characters A-Z, a-z, 0-9, _ and - are allowed. The header is useful to ensure that the request comes from a webhook set by you.
    async def set_webhook(self, url: str, secret_token: str) -> Dict[str, Any]:
        payload = {
            "url": url,
            "secret_token": secret_token
        }

        try:
            r = await self._client.post(f"/setWebhook", data=payload)
            data = r.json()

            if not data.get("ok"):
                raise RuntimeError(f"Telegram API error: set webhook failed, {data.get('description')}")

            return data["result"]
        except Exception as e:
            logger.exception(f"Failed to set Telegram webhook: {e}")
            raise
    
    async def get_updates(self, offset=None):
        params = {
            "offset": offset,
        }
        r = await self._client.get(f"/getUpdates", params=params)
        return r.json()

    async def send_welcome_message(self, chat_id: int):
        text = (
            "Welcome to Centpai!\n\n"
            "Tap a button below or enter a command to get started:\n\n"
            + COMMANDS_TEXT
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Join Group", "callback_data": "join_group"}
                ],
                [
                    {"text": "Leave Group", "callback_data": "leave_group"}
                ],
                [
                    {"text": "View Expenses Breakdown", "callback_data": "view_expenses_breakdown"}
                ],
                [
                    {"text": "Help", "callback_data": "help"}
                ]
            ]
        }

        await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    
    async def send_home_message(self, chat_id: int):
        current_members = self.group[chat_id]
        text = (
            "Welcome to Centpai!\n\n"
            "Current members:\n"
            + "\n".join(f"• {member}" for member in current_members) +
            "\nStatus:\n"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Join Group", "callback_data": "join_group"}
                ],
                [
                    {"text": "Leave Group", "callback_data": "leave_group"}
                ],
                [
                    {"text": "View Expenses Breakdown", "callback_data": "view_expenses_breakdown"}
                ],
                [
                    {"text": "Help", "callback_data": "help"}
                ]
            ]
        }

        await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    

    async def answer_callback_query(self, callback_query_id: str, text: str | None = None, show_alert: bool = False, url: str | None = None, cache_time: int = 0):
        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id
        }

        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = show_alert
        if url:
            payload["url"] = url
        if cache_time:
            payload["cache_time"] = cache_time
        
        await self._client.post(f"/answerCallbackQuery", json=payload)
    

    async def setMyCommands(self, commands:List[Dict[str, str]], scope: Optional[Dict[str, Any]] = None, language_code: Optional[str] = None):
        
        payload: dict[str, Any] = {
            "commands": commands
        }

        if scope:
            payload["scope"] = scope
        if language_code:
            payload["language_code"] = language_code
        
        await self._client.post(f"/setMyCommands", json=payload)
    
    def add_user_to_group(self, username: str, chat_id: int):
        self.group[chat_id].add(username)
    

    def remove_user_from_group(self, username: str, chat_id: int):
        self.group[chat_id].discard(username)

    def is_group_empty(self, chat_id: int):
        if len(self.group[chat_id]) == 0:
            return True

        return False

    def add_expense(self, chat_id: int, args: str):
        if (self.is_group_empty(chat_id)):
            return [False, "You cannot enter an expense until there is at least 1 person in your group."]
        
        args = args.split()
        uid = uuid.uuid4().hex[:8]

        if len(args) == 2:
            try:
                price = float(args[1])
            except:
                return [False, "Enter an appropriate price amount."]
            self.expenses[chat_id][uid] = {
                "category": args[0],
                "price": price,
            }
            #calculate and add to group
            return [True, "Expense added."]

        return [False, "Try again."]


    async def send_expense_view_message(self, chat_id: int):
        current_expenses = self.expenses.get(chat_id, {})
        if not current_expenses:
            text = "No expenses added yet."
        else:
            expense_lines = []
            for uid, expense in current_expenses.items():
                category = expense["category"]
                price = expense["price"]
                expense_lines.append(f"• {uid} | {category} — ${price:.2f}")

            text = "Current expenses:\n" + "\n".join(expense_lines)

        await self.send_message(chat_id, text)