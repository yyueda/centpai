import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException, Request
from app.core.middleware import RateLimiterMiddleware
from app.features.expenses.jobs import send_reminder
from app.features.expenses.repo import ExpensesRepository
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
from app.features.telegram.commands.reminders import (
    handleSetReminder,
    handleRemoveReminder,
)
from app.features.telegram.context import build_context_from_update
from app.features.telegram.schemas import Update
from app.core.logging import setup_logging
from app.features.telegram import client
from app.core.config import settings
from app.db.database import SessionLocal, init_db

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

    scheduler = AsyncIOScheduler()

    # Re-register all existing reminders from DB
    async with SessionLocal() as session:
        repo = ExpensesRepository(session)
        reminders = await repo.get_all_reminders()
        for reminder in reminders:
            hour, minute = reminder.remind_time.split(":")
            scheduler.add_job(
                send_reminder,
                "cron",
                hour=int(hour),
                minute=int(minute),
                timezone="UTC",
                args=[tg, reminder.chat.telegram_chat_id],
                id=f"reminder_{reminder.chat.telegram_chat_id}",
                replace_existing=True,
            )

    scheduler.start()
    app.state.telegram = tg
    app.state.scheduler = scheduler
    yield

    scheduler.shutdown()
    await tg.aclose()


app = FastAPI(lifespan=lifespan)
app.add_middleware(RateLimiterMiddleware)


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
    scheduler: AsyncIOScheduler = request.app.state.scheduler

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
                        await handleListMembers(ctx, tg, svc)
                    case CommandName.LEAVE:
                        await handleLeave(ctx, tg, svc)
                    case CommandName.HELP:
                        await handleHelp(ctx, tg)
                    case CommandName.JOIN:
                        await handleJoin(ctx, tg, svc)
                    case CommandName.EXPENSE_ADD:
                        await handleAddExpense(
                            ctx, tg, svc, command.args, command.mentioned_usernames
                        )
                    case CommandName.EXPENSE_VIEW:
                        await handleListExpenses(ctx, tg, svc)
                    case CommandName.EXPENSE_REMOVE:
                        await handleRemoveExpense(ctx, tg, svc, command.args)
                    case CommandName.PAY:
                        await handlePay(ctx, tg, svc, command.args)
                    case CommandName.DEBTS:
                        await handleDebts(ctx, tg, svc)
                    case CommandName.REMIND:
                        await handleSetReminder(ctx, tg, svc, scheduler, command.args)
                    case CommandName.REMIND_OFF:
                        await handleRemoveReminder(ctx, tg, svc, scheduler)

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

            try:
                match data:
                    case "join":
                        await handleJoin(ctx, tg, svc)
                    case "leave":
                        await handleLeave(ctx, tg, svc)
                    case "view":
                        await handleListExpenses(ctx, tg, svc)
                    case "debts":
                        await handleDebts(ctx, tg, svc)
                    case "help":
                        await handleHelp(ctx, tg)
            finally:
                # After the user presses a callback button, Telegram clients will display a progress bar until you call answerCallbackQuery.
                # It is, therefore, necessary to react by calling answerCallbackQuery even if no notification to the user is needed
                await tg.answer_callback_query(callback_query_id=callback_id)
    except Exception:
        logger.exception("Failed to handle update %s", update.update_id)

    return {"ok": True}
