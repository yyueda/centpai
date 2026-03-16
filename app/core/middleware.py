from collections import defaultdict
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.features.telegram import client
from app.features.telegram.schemas import Update

logger = logging.getLogger("centpai")

RATE_LIMIT = 5  # max requests
WINDOW_SECS = 10  # per window


class RateLimiterMiddleware(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[int, list[float]] = defaultdict(list)

    def _get_chat_id(self, body: bytes) -> int | None:
        try:
            update = Update.model_validate_json(body)
            if update.message:
                return update.message.chat.id
            if update.callback_query:
                return update.callback_query.message.chat.id
            if update.my_chat_member:
                return update.my_chat_member.chat.id
        except Exception:
            return None

    # Sliding window algo
    def _is_rate_limited(self, chat_id: int) -> bool:
        now = time.monotonic()
        timestamps = self._buckets[chat_id]
        self._buckets[chat_id] = [t for t in timestamps if now - t < WINDOW_SECS]
        if len(self._buckets[chat_id]) >= RATE_LIMIT:
            return True
        self._buckets[chat_id].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        body = await request.body()

        chat_id = self._get_chat_id(body)
        if chat_id and self._is_rate_limited(chat_id):
            tg: client.TelegramAPI = request.app.state.telegram
            await tg.send_message(
                chat_id=chat_id,
                text=f"Please wait again before sending requests.",
            )

            logger.warning("Rate limit exceeded for chat_id=%s", chat_id)
            return Response(
                status_code=200
            )  # Have to return 2XY status code for telegram to stop retrying

        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)
        return await call_next(request)
