from aiogram import BaseMiddleware
from aiogram.types import Update
from typing import Callable, Dict, Any, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем session_factory из workflow_data диспетчера
        session_factory = data["dispatcher"].workflow_data["session_factory"]

        async with session_factory() as session:
            data["db_session"] = session
            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
