import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.errors import DomainError
from app.features.expenses.jobs import send_reminder
from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext

logger = logging.getLogger("centpai")


def _parse_remind_time(time_str: str) -> str:
    try:
        parsed = datetime.strptime(time_str, "%H:%M")
        return parsed.strftime("%H:%M")
    except ValueError:
        raise ValueError("Invalid time format. Use HH:MM in UTC (e.g. 09:00).")


async def handleSetReminder(
    ctx: TgContext,
    messenger: Messenger,
    svc: ExpensesService,
    scheduler: AsyncIOScheduler,
    args: list[str],
) -> None:
    if not args:
        await messenger.send_message(
            ctx.tg_chat_id,
            "Usage: /remind HH:MM (UTC)\nExample: /remind 09:00",
            reply_to_message_id=ctx.message_id,
            reply_markup={
                "force_reply": True,
                "input_field_placeholder": "/remind <HH:MM>",
                "selective": True,
            },
        )
        return

    try:
        remind_time = _parse_remind_time(args[0])
        await svc.set_reminder(ctx.tg_chat_id, ctx.tg_user_id, remind_time)

        hour, minute = remind_time.split(":")
        scheduler.add_job(
            send_reminder,
            "cron",
            hour=int(hour),
            minute=int(minute),
            timezone="UTC",
            args=[messenger, ctx.tg_chat_id],
            id=f"reminder_{ctx.tg_chat_id}",
            replace_existing=True,
        )

        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"✅ Daily debt reminder set for <code>{remind_time} UTC</code>.\nUse /remindoff to cancel.",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
    except ValueError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {str(e)}",
            reply_to_message_id=ctx.message_id,
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {e.message}",
            reply_to_message_id=ctx.message_id,
        )


async def handleRemoveReminder(
    ctx: TgContext,
    messenger: Messenger,
    svc: ExpensesService,
    scheduler: AsyncIOScheduler,
) -> None:
    try:
        deleted = await svc.remove_reminder(ctx.tg_chat_id, ctx.tg_user_id)

        job_id = f"reminder_{ctx.tg_chat_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

        if deleted:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="Daily reminder cancelled.",
                reply_to_message_id=ctx.message_id,
            )
        else:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="No reminder is currently set for this chat.",
                reply_to_message_id=ctx.message_id,
            )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {e.message}",
            reply_to_message_id=ctx.message_id,
        )
