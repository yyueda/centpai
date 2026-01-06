from typing import Union
from fastapi import FastAPI, Request
from core.logging import setup_logging
from features.telegram import client
from core.config import settings

setup_logging()

async def lifespan(app: FastAPI):
    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.set_webhook(
        url="https://0e5d760fddfa.ngrok-free.app/webhook", 
        secret_token="test_secret")
    app.state.telegram = tg
    yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/webhook")
async def read_webhook(update: dict, request: Request):
    tg = request.app.state.telegram

    if "my_chat_member" in update:
        event = update["my_chat_member"]

        old_status = event["old_chat_member"]["status"]
        new_status = event["new_chat_member"]["status"]

        if old_status in ("kicked", "left") and new_status in ("member", "administrator"):
            #bot just added to the group, send welcome message
            chat_id = event["chat"]["id"]
            await tg.send_welcome_message(chat_id=chat_id)

    if "callback_query" in update:
        cq = update["callback_query"]

        callback_id = cq["id"]
        data = cq.get("data")          
        chat_id = cq["message"]["chat"]["id"]
        username = cq["from"]["username"]

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
            
    return {"ok": True}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
