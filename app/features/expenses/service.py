from app.features.expenses.repo import ExpensesRepository
from sqlalchemy.ext.asyncio import AsyncSession

class ExpensesService:
    def __init__(self, db: AsyncSession, repo: ExpensesRepository):
        self.db = db
        self.repo = repo

    # ------------------------------------------------------------------
    # MEMBERSHIP/INIT
    # ------------------------------------------------------------------

    # Executed when bot is first added: initialise new data in db
    async def init(
        self,
        tg_chat_id: int,
        tg_user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> None:
        await self.db.begin()

        try:
            chat = await self.repo.get_or_create_chat(tg_chat_id)
            user = await self.repo.get_or_create_user(
                tg_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )

            await self.repo.add_member(chat.id, user.id)
            await self.repo.create_balance(chat.id, user.id)
        except:
            await self.db.rollback()
            raise
        else:
            await self.db.commit()
