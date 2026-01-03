from typing import Union
from fastapi import FastAPI, Request
from core.logging import setup_logging
from features.telegram import client
from core.config import settings

setup_logging()
app = FastAPI()

@app.on_event("startup")
async def startup():
    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.set_webhook(
        url="https://dc0e891a6de9.ngrok-free.app/webhook", 
        secret_token="test_secret")
    app.state.telegram = tg


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/webhook")
async def read_webhook(update: dict, request: Request):
    if "my_chat_member" in update:
        event = update["my_chat_member"]

        old_status = event["old_chat_member"]["status"]
        new_status = event["new_chat_member"]["status"]

        if old_status in ("kicked", "left") and new_status in ("member", "administrator"):
            #bot just added to the group, send welcome message
            chat_id = event["chat"]["id"]
            tg = request.app.state.telegram
            await tg.send_welcome_message(chat_id=chat_id)
            
    return {"ok": True}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
