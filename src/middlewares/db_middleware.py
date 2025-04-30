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
        async_session = data["dp"].workflow_data.get("db_session")

        # Создаем новую сессию для обработки события
        async with async_session() as session:
            # Передаем сессию в данные хендлера
            data["db_session"] = session
            # Вызываем хендлер
            return await handler(event, data)
