from aiogram import BaseMiddleware
from aiogram.types import Update
from typing import Callable, Dict, Any, Awaitable


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        db_manager = data["dispatcher"].workflow_data["db_manager"]

        session_generator = db_manager.get_async_session()
        async for session in session_generator:
            data["db_session"] = session
            try:
                return await handler(event, data)
            finally:
                await session.close()
