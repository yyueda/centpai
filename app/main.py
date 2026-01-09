from contextlib import asynccontextmanager
from typing import Union
from fastapi import Depends, FastAPI, Request
from app.features.expenses.repo import ExpensesRepository
from app.features.expenses.service import ExpensesService
from app.features.telegram.commands.admin import handleHelp, handleInit
from app.features.telegram.commands.command_parser import CommandName, parse_command
from app.features.telegram.commands.members import handleJoin
from app.features.telegram.context import build_context_from_update
from features.telegram.schemas import Update
from core.logging import setup_logging
from features.telegram import client
from core.config import settings
from db.database import get_session, init_db
from sqlalchemy.ext.asyncio import AsyncSession

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.setMyCommands(tg.commands)
    await tg.set_webhook(
        url=f"{settings.NGROK_URL}/webhook", 
        secret_token="test_secret")
    app.state.telegram = tg
    yield

    # Cleanup
    await tg.aclose()

app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/webhook")
async def read_webhook(
    request: Request,
    update: Update,
    session: AsyncSession = Depends(get_session)
):
    ctx = build_context_from_update(update)
    tg: client.TelegramAPI = request.app.state.telegram
    repo = ExpensesRepository(session)
    svc = ExpensesService(session, repo)

    # For initial welcome message
    if update.my_chat_member:
        bot_status_change = update.my_chat_member

        old_status = bot_status_change.old_chat_member.status
        new_status = bot_status_change.new_chat_member.status

        if old_status in ("kicked", "left") and new_status in ("member", "administrator"):
            # bot just added to the group, send welcome message
            await handleInit(ctx, tg, svc)
    
    if update.message:
        command = parse_command(update.message)

        if command:
            match command.name:
                case CommandName.HELP:
                    await handleHelp(ctx, tg)
                case CommandName.JOIN:
                    await handleJoin(ctx, tg, svc)
                # case CommandName.EXPENSE_ADD:
                #     status, message = tg.add_expense(chat_id=chat_id, args=args)
                #     await tg.send_message(chat_id=chat_id, text=message)
                # case CommandName.EXPENSE_VIEW:
                #     await tg.send_expense_view_message(chat_id)

            return {"ok": True}

    # For button clicks
    # if update.callback_query:
    #     cq = update.callback_query
    #     callback_id = cq.id
    #     data = cq.data

    #     # message can be None in some callback scenarios
    #     if cq.message is None:
    #         await tg.answer_callback_query(callback_query_id=callback_id, text="Unsupported action.")
    #         return {"ok": True}

    #     chat_id = cq.message.chat.id
    #     username = cq.from_.username

    #     if data == "join_group":
    #         tg.add_user_to_group(username=username, chat_id=chat_id)
    #         await tg.send_message(chat_id=chat_id, text=f"{username} joined the group.")
    #         await tg.send_home_message(chat_id=chat_id)
    #     elif data == "leave_group":
    #         tg.remove_user_from_group(username=username, chat_id=chat_id)
    #         await tg.send_message(chat_id=chat_id, text=f"{username} left the group.")
    #         await tg.send_home_message(chat_id=chat_id)
    #     elif data == "help":
    #         await tg.send_message(chat_id=chat_id, text="Centpai works like this: ...")
        
        
    #     await tg.answer_callback_query(callback_query_id=callback_id)
    

            
    return {"ok": True}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
