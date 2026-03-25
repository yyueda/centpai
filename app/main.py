import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Union
from fastapi import Depends, FastAPI, Request
from app.core.middleware import RateLimiterMiddleware
from app.features.expenses.repo import ExpensesRepository, get_repo
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
from app.features.telegram.context import build_context_from_update, text_with_user_greeting
from app.features.telegram.schemas import Update
from app.core.logging import setup_logging
from app.features.telegram import client
from app.core.config import settings
from app.db.database import init_reset_db_dev

setup_logging()
logger = logging.getLogger("centpai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_reset_db_dev()  # dev purposes
    # await init_db()

    tg = client.TelegramAPI(settings.BOT_TOKEN)
    await tg.setMyCommands(tg.commands)
    await tg.set_webhook(
        url=f"{settings.WEBHOOK_URL}/webhook", secret_token=settings.WEBHOOK_SECRET
    )
    app.state.telegram = tg
    app.state.pending_actions = {}  # (chat_id, user_id) -> action
    yield

    # Cleanup
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
            pending_action = request.app.state.pending_actions.get(
                (ctx.tg_chat_id, ctx.tg_user_id)
            )

            # Prioritize explicit commands even during pending actions
            command = parse_command(update.message)
            if command:
                if pending_action is not None:
                    request.app.state.pending_actions.pop((ctx.tg_chat_id, ctx.tg_user_id), None)

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
                        await handleDebts(ctx, tg, svc, command.args)

                return {"ok": True}

            if pending_action == "add_expense":
                text = update.message.text or ""
                normalized = text.strip().lower()
                if normalized == "/cancel" or normalized.startswith("/cancel@") or normalized == "cancel":
                    request.app.state.pending_actions.pop((ctx.tg_chat_id, ctx.tg_user_id), None)
                    await tg.send_message(
                        ctx.tg_chat_id,
                        "✅ Add expense canceled. Type /help to see commands.",
                        reply_to_message_id=ctx.message_id,
                    )
                    return {"ok": True}

                args = text.strip().split()
                mentioned_usernames = [t[1:] for t in args if t.startswith("@")]

                await handleAddExpense(ctx, tg, svc, args, mentioned_usernames)
                request.app.state.pending_actions.pop((ctx.tg_chat_id, ctx.tg_user_id), None)
                return {"ok": True}

        # For button clicks
        if update.callback_query:
            cq = update.callback_query
            data = cq.data

            # message can be None in some callback scenarios
            if cq.message is None:
                return {"ok": True}

            if not data:
                await tg.send_message(
                    ctx.tg_chat_id,
                    "Invalid button action.",
                    reply_to_message_id=cq.message.message_id,
                )
                return {"ok": True}

            action = data
            target_user_id = None
            if ":" in data:
                action, owner = data.split(":", 1)
                try:
                    target_user_id = int(owner)
                except ValueError:
                    target_user_id = None

            if target_user_id is not None and target_user_id != ctx.tg_user_id:
                await tg.send_message(
                    ctx.tg_chat_id,
                    "This menu is reserved for the user who opened it. Please send /help to open your own menu.",
                    reply_to_message_id=cq.message.message_id,
                )
                return {"ok": True}

            match action:
                case "join_group":
                    await handleJoin(ctx, tg, svc)
                case "leave_group":
                    await handleLeave(ctx, tg, svc)
                case "add_expense":
                    try:
                        members = await svc.get_members(ctx.tg_chat_id)
                    except Exception:
                        members = []

                    if ctx.username not in members:
                        await tg.send_message(
                            ctx.tg_chat_id,
                            text_with_user_greeting(
                                ctx,
                                "You are not registered yet. Please join first with /join.",
                            ),
                            reply_to_message_id=ctx.message_id,
                        )
                        return {"ok": True}

                    request.app.state.pending_actions[(ctx.tg_chat_id, ctx.tg_user_id)] = "add_expense"
                    await tg.send_message(
                        ctx.tg_chat_id,
                        text_with_user_greeting(
                            ctx,
                            "Enter the expense details as: <amount> <description> [@user1 @user2].\n"
                            "For example: 25.50 Lunch @alice @bob\n\n"
                            "Send /cancel to abort.",
                        ),
                        reply_to_message_id=ctx.message_id,
                    )
                case "view_expenses_breakdown":
                    await handleListExpenses(ctx, tg, svc)
                case "help":
                    await handleHelp(ctx, tg)
    except Exception:
        logger.exception("Failed to handle update %s", update.update_id)

    return {"ok": True}
