from contextlib import asynccontextmanager
from typing import Union
from fastapi import FastAPI, Request
from app.features.telegram.schemas import Update
from core.logging import setup_logging
from features.telegram import client
from core.config import settings

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.set_webhook(
        url=settings.NGROK_URL, 
        secret_token="test_secret")
    app.state.telegram = tg
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/webhook")
async def read_webhook(update: Update, request: Request):
    tg = request.app.state.telegram

    if update.my_chat_member:
        bot_status_change = update.my_chat_member

        old_status = bot_status_change.old_chat_member.status
        new_status = bot_status_change.new_chat_member.status

        if old_status in ("kicked", "left") and new_status in ("member", "administrator"):
            #bot just added to the group, send welcome message
            chat_id = bot_status_change.chat.id
            await tg.send_welcome_message(chat_id=chat_id)

    if update.callback_query:
        cq = update.callback_query
        callback_id = cq.id
        data = cq.data

        # message can be None in some callback scenarios
        if cq.message is None:
            await tg.answer_callback_query(callback_query_id=callback_id, text="Unsupported action.")
            return {"ok": True}

        chat_id = cq.message.chat.id
        username = cq.from_.username

        if data == "join_group":
            tg.add_user_to_group(username=username, chat_id=chat_id)
            await tg.send_message(chat_id=chat_id, text=f"{username} joined the group.")
            await tg.send_group_message(chat_id=chat_id)
        elif data == "leave_group":
            tg.remove_user_from_group(username=username, chat_id=chat_id)
            await tg.send_message(chat_id=chat_id, text=f"{username} left the group.")
            await tg.send_group_message(chat_id=chat_id)
        elif data == "add_expense":
            await tg.send_expense_message(chat_id=chat_id)
        elif data == "how_it_works":
            await tg.send_message(chat_id=chat_id, text="Centpai works like this: ...")
        
        
        await tg.answer_callback_query(callback_query_id=callback_id)
            
    return {"ok": True}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
