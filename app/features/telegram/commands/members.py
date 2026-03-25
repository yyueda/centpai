from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext, text_with_user_greeting
from app.core.errors import DomainError
from app.features.expenses.errors import ChatNotFound


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
            text=text_with_user_greeting(ctx, f"✅ @{ctx.username} joined."),
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=text_with_user_greeting(ctx, f"❌ {e.message}"),
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
                text=text_with_user_greeting(
                    ctx,
                    "<b>Current members:</b>\n"
                    + "\n".join(f"• <b>{member}</b>" for member in members),
                ),
                reply_to_message_id=ctx.message_id,
                parse_mode="HTML",
            )
        else:
            await messenger.send_message(
                chat_id=ctx.tg_chat_id,
                text=text_with_user_greeting(ctx, "No members found."),
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
            text=text_with_user_greeting(ctx, f"@{ctx.username} left."),
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
    except DomainError as e:
        await messenger.send_message(
            chat_id=ctx.tg_chat_id,
            text=text_with_user_greeting(ctx, f"❌ {e.message}"),
            reply_to_message_id=ctx.message_id,
            parse_mode="HTML",
        )
