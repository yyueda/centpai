import logging

from app.db.database import SessionLocal
from app.features.expenses.repo import ExpensesRepository
from app.features.expenses.service import ExpensesService
from app.features.telegram.client import TelegramAPI

logger = logging.getLogger("centpai")

async def send_reminder(tg: TelegramAPI, tg_chat_id: int) -> None:
    async with SessionLocal() as session:
        repo = ExpensesRepository(session)
        svc = ExpensesService(repo)
        try:
            lines = ["<b>Daily Debt Reminder</b>\n"]
            debts = await svc.get_simplified_debts(tg_chat_id)
            if not debts:
                lines.append("No debts.")
                await tg.send_message(
                    chat_id=tg_chat_id,
                    text="\n".join(lines),
                    parse_mode="HTML",
                )
                return

            for d in debts:
                lines.append(
                    f"• <b>{d.from_user}</b> ---> <b>{d.to_user}</b> <code>${d.amount}</code>"
                )

            await tg.send_message(
                chat_id=tg_chat_id,
                text="\n".join(lines),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Failed to send reminder for chat %s", tg_chat_id)
