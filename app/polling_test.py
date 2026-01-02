import asyncio
import httpx
import time

from telegram.client import tg
from telegram.schemas import Update

async def main():
    print("Polling...")
    last_update_id = None

    while True:
        data = await tg.get_updates(offset=last_update_id)

        if not data["ok"]:
            print("Error:", data)
            time.sleep(1)
            continue

        for upd in data["result"]:
            print("Got update:", upd)

            # Remember update_id so Telegram doesn't resend the same updates
            update_obj = Update.model_validate(upd)
            last_update_id = update_obj.update_id + 1

            if update_obj.message:
                chat_id = update_obj.message.chat.id
                text = update_obj.message.text

                # Echo reply
                await tg.send_message(chat_id, f"You said: {text}")

        time.sleep(0.5)

asyncio.run(main())
