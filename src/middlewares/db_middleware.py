from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Dict, Any, Awaitable


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        # Получаем фабрику сессий из данных диспетчера
        async_session = data["dispatcher"].workflow_data.get("db_manager")

        # Создаем новую сессию для обработки события
        # session = async_session.get_async_session()
        async for session in async_session.get_async_session():
             data["db_session"] = session

        return await handler(event, data)
