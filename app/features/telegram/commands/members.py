from app.features.expenses.service import ExpensesService
from app.features.telegram.client import Messenger
from app.features.telegram.context import TgContext

async def handleJoin(ctx: TgContext, messenger: Messenger, svc: ExpensesService) -> None:
    await svc.add_member(
        ctx.tg_chat_id,
        ctx.tg_user_id,
        username=ctx.username,
        first_name=ctx.first_name,
        last_name=ctx.last_name
    )
    await messenger.send_message(
        chat_id=ctx.tg_chat_id, 
        text=f"{ctx.username} joined."
    )

# async def send_home_message(chat_id: int, messenger: Messenger):
        
#         text = (
#             "Welcome to Centpai!\n\n"
#             "Current members:\n"
#             + "\n".join(f"• {member}" for member in current_members) +
#             "\nStatus:\n"
#         )

#         keyboard = {
#             "inline_keyboard": [
#                 [
#                     {"text": "Join Group", "callback_data": "join_group"}
#                 ],
#                 [
#                     {"text": "Leave Group", "callback_data": "leave_group"}
#                 ],
#                 [
#                     {"text": "View Expenses Breakdown", "callback_data": "view_expenses_breakdown"}
#                 ],
#                 [
#                     {"text": "Help", "callback_data": "help"}
#                 ]
#             ]
#         }

#         await self.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

async def handleLeave(ctx: TgContext, messenger: Messenger, svc: ExpensesService) -> None:
    return
