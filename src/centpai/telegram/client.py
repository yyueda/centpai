import httpx
import logging
from centpai.config import settings
from typing import Any, Dict

logger = logging.getLogger("telegram")

BASE = "https://api.telegram.org"

class TelegramAPI:
    def __init__(self, token: str, timeout: float = 10.0):
        self.base = f"{BASE}/bot{token}"
        self._client = httpx.AsyncClient(base_url=self.base, timeout=timeout)
    
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

    async def send_welcome_message(self, chat_id:str):
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