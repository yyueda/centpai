import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from app.core.middleware import RateLimiterMiddleware
from app.features.expenses.service import ExpensesService, get_service
from app.features.telegram.commands.admin import handleHelp, handleInit
from app.features.telegram.commands.command_parser import CommandName, parse_command
from app.features.telegram.commands.expenses import (
    handleAddExpense,
    handleDebts,
    handleListExpenses,
    handleRemoveExpense,
    handlePay,
)
from app.features.telegram.commands.members import (
    handleJoin,
    handleLeave,
    handleListMembers,
)
from app.features.telegram.context import build_context_from_update
from app.features.telegram.schemas import Update
from app.core.logging import setup_logging
from app.features.telegram import client
from app.core.config import settings
from app.db.database import init_db
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.metrics import commands_total, command_duration_seconds

setup_logging()
logger = logging.getLogger("centpai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.setMyCommands(tg.commands)
    await tg.set_webhook(
        url=f"{settings.WEBHOOK_URL}/webhook", secret_token=settings.WEBHOOK_SECRET
    )
    app.state.telegram = tg
    yield

    await tg.aclose()


# For prometheus
@asynccontextmanager
async def track_command(command: str):
    with command_duration_seconds.labels(command=command).time():
        try:
            yield
        finally:
            commands_total.labels(command=command).inc()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RateLimiterMiddleware)
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def read_root():
    return {"status": "ok"}


@app.post("/webhook")
async def read_webhook(
    request: Request,
    update: Update,
    svc: ExpensesService = Depends(get_service),
):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    ctx = build_context_from_update(update)
    if ctx is None:
        return {"ok": True}
    tg: client.TelegramAPI = request.app.state.telegram

    # For initial welcome message
    if update.my_chat_member:
        bot_status_change = update.my_chat_member

        old_status = bot_status_change.old_chat_member.status
        new_status = bot_status_change.new_chat_member.status

        if old_status in ("kicked", "left") and new_status in (
            "member",
            "administrator",
        ):
            # bot just added to the group, send welcome message
            await handleInit(ctx, tg, svc)

    try:
        if update.message:
            command = parse_command(update.message)

            if command:
                match command.name:
                    case CommandName.MEMBERS:
                        async with track_command("/members"):
                            await handleListMembers(ctx, tg, svc)
                    case CommandName.LEAVE:
                        async with track_command("/leave"):
                            await handleLeave(ctx, tg, svc)
                    case CommandName.HELP:
                        async with track_command("/help"):
                            await handleHelp(ctx, tg)
                    case CommandName.JOIN:
                        async with track_command("/join"):
                            await handleJoin(ctx, tg, svc)
                    case CommandName.EXPENSE_ADD:
                        async with track_command("/add_expense"):
                            await handleAddExpense(
                                ctx, tg, svc, command.args, command.mentioned_usernames
                            )
                    case CommandName.EXPENSE_VIEW:
                        async with track_command("/view_expenses"):
                            await handleListExpenses(ctx, tg, svc)
                    case CommandName.EXPENSE_REMOVE:
                        async with track_command("/remove_expense"):
                            await handleRemoveExpense(ctx, tg, svc, command.args)
                    case CommandName.PAY:
                        async with track_command("/pay"):
                            await handlePay(ctx, tg, svc, command.args)
                    case CommandName.DEBTS:
                        async with track_command("/debts"):
                            await handleDebts(ctx, tg, svc, command.args)

                return {"ok": True}

        # For button clicks
        if update.callback_query:
            cq = update.callback_query
            callback_id = cq.id
            data = cq.data

            # message can be None in some callback scenarios
            if cq.message is None:
                await tg.answer_callback_query(
                    callback_query_id=callback_id, text="Unsupported action."
                )
                return {"ok": True}

            match data:
                case "join_group":
                    await handleJoin(ctx, tg, svc)
                case "leave_group":
                    await handleLeave(ctx, tg, svc)
                case "view_expenses_breakdown":
                    await handleListExpenses(ctx, tg, svc)
                case "help":
                    await handleHelp(ctx, tg)
    except Exception:
        logger.exception("Failed to handle update %s", update.update_id)

    return {"ok": True}
