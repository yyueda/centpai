import httpx
import logging
from typing import Any, Dict
import collections

logger = logging.getLogger("telegram")

BASE = "https://api.telegram.org"

class TelegramAPI:
    def __init__(self, token: str, timeout: float = 10.0):
        self.base = f"{BASE}/bot{token}"
        self._client = httpx.AsyncClient(base_url=self.base, timeout=timeout)
        self.group = collections.defaultdict(set)
        self.expenses = collections.defaultdict(int)
    
    async def aclose(self) -> None:
        """Close the underlying HTTP client (e.g. on shutdown)."""
        await self._client.aclose()
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_to_message_id: int | None = None,
        reply_markup: dict | None=None,
        parse_mode: str | None = "HTML"
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
            "Tap a button below to get started:"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Join Group", "callback_data": "join_group"}
                ],
                [
                    {"text": "How it works", "callback_data": "how_it_works"}
                ]
            ]
        }

        await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    
    async def send_group_message(self, chat_id: int):
        current_members = self.group[chat_id]
        text = (
            "Welcome to Centpai!\n\n"
            "Current members:\n"
            + "\n".join(f"• {member}" for member in current_members) +
            "\n\nExpenses:\n"
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
                    {"text": "Add Expense", "callback_data": "add_expense"}
                ],
                [
                    {"text": "Remove Expense", "callback_data": "remove_expense"}
                ],
                [
                    {"text": "Settle Up", "callback_data": "settle_up"}
                ],
                [
                    {"text": "How it works", "callback_data": "how_it_works"}
                ]
            ]
        }

        await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    

    async def send_expense_message(self, chat_id: int):
        current_members = self.group[chat_id]
        text = (
            "Welcome to Centpai!\n\n"
            "Current members:\n"
            + "\n".join(f"• {member}" for member in current_members) +
            "\n\nExpenses:\n"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "Food & Drink", "callback_data": "add_fooddrink_expense"}
                ],
                [
                    {"text": "Transport", "callback_data": "add_transport_expense"}
                ],
                [
                    {"text": "Accomodation", "callback_data": "add_accomodation_expense"}
                ],
                [
                    {"text": "Entertainment", "callback_data": "add_entertainment_expense"}
                ],
                [
                    {"text": "Shopping", "callback_data": "add_shopping_expense"}
                ],
                [
                    {"text": "Others", "callback_data": "add_others_expense"}
                ]
            ]
        }

        await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    
    async def answer_callback_query(self, callback_query_id: str, text: str | None = None, show_alert: bool = False, url: str | None = None, cache_time: int = 0):
        payload = {
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
    
    def add_user_to_group(self, username: str, chat_id: int):
        self.group[chat_id].add(username)
    

    def remove_user_from_group(self, username: str, chat_id: int):
        self.group[chat_id].discard(username)
