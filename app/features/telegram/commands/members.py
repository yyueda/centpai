from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext
from app.core.errors import DomainError


async def handleJoin(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    try:
        await svc.add_member(
            ctx.tg_chat_id,
            ctx.tg_user_id,
            username=ctx.username,
            first_name=ctx.first_name,
            last_name=ctx.last_name,
        )
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"✅ <b>{ctx.username}</b> joined.",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {e.message}",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )


async def handleListMembers(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    try:
        members = await svc.get_members(ctx.tg_chat_id)

        if members:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="<b>Current members:</b>\n"
                + "\n".join(f"• <b>{member}</b>" for member in members),
                reply_to_message_id=ctx.message_id,
                parse_mode="HTML",
            )
        else:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text="No members found.",
                reply_to_message_id=ctx.message_id,
            )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {e.message}",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )


async def handleLeave(
    ctx: TgContext, messenger: Messenger, svc: ExpensesService
) -> None:
    try:
        await svc.remove_member(ctx.tg_chat_id, ctx.tg_user_id)
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"<b>{ctx.username}</b> left.",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=f"❌ {e.message}",
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
