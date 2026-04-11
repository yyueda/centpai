import httpx
import logging
from typing import Any, Dict, List, Optional, Protocol
import collections

logger = logging.getLogger("telegram")

BASE = "https://api.telegram.org"


# Interface for easier testing
class Messenger(Protocol):
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]: ...


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
            {"command": "members", "description": "List members in chat"},
            {"command": "add", "description": "Add an expense"},
            {"command": "view", "description": "View all expenses"},
            {"command": "pay", "description": "Pay a debt"},
            {"command": "debts", "description": "Get simplified debts"},
            {
                "command": "remind",
                "description": "Set a daily debt reminder (HH:MM UTC)",
            },
            {"command": "remindoff", "description": "Cancel the daily reminder"},
        ]

    async def aclose(self) -> None:
        """Close the underlying HTTP client (e.g. on shutdown)."""
        await self._client.aclose()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
        reply_markup: dict | None = None,
        parse_mode: str | None = None,
    ) -> Dict[str, Any]:

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_to_message_id:
            payload["reply_parameters"] = {"message_id": reply_to_message_id}

        try:
            r = await self._client.post(f"/sendMessage", json=payload)
            r.raise_for_status()

            data = r.json()
            if not data.get("ok"):
                raise RuntimeError(
                    f"Telegram API error: send message failed, {data.get('description')}"
                )

            return data
        except Exception as e:
            logger.exception(f"Failed to send Telegram message: {e}")
            raise

    # A secret token to be sent in a header “X-Telegram-Bot-Api-Secret-Token” in every webhook request, 1-256 characters. Only characters A-Z, a-z, 0-9, _ and - are allowed. The header is useful to ensure that the request comes from a webhook set by you.
    async def set_webhook(self, url: str, secret_token: str) -> Dict[str, Any]:
        payload = {"url": url, "secret_token": secret_token}

        try:
            r = await self._client.post(f"/setWebhook", data=payload)
            data = r.json()

            if not data.get("ok"):
                raise RuntimeError(
                    f"Telegram API error: set webhook failed, {data.get('description')}"
                )

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

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
        url: str | None = None,
        cache_time: int = 0,
    ):
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}

        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = show_alert
        if url:
            payload["url"] = url
        if cache_time:
            payload["cache_time"] = cache_time

        await self._client.post(f"/answerCallbackQuery", json=payload)

    async def setMyCommands(
        self,
        commands: List[Dict[str, str]],
        scope: Optional[Dict[str, Any]] = None,
        language_code: Optional[str] = None,
    ):

        payload: dict[str, Any] = {"commands": commands}

        if scope:
            payload["scope"] = scope
        if language_code:
            payload["language_code"] = language_code

        await self._client.post(f"/setMyCommands", json=payload)
