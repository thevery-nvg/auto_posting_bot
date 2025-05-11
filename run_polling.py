import asyncio

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from aiogram.filters import Command
from aiogram import types

from core.database import init_db, DatabaseManager
from core.models import User, UserRole
from src.middlewares.logging_middleware import LoggingMiddleware
from src.middlewares.db_middleware import DatabaseMiddleware
from src.utils.logger import setup_logging
from src.utils.smart_session import SmartAiohttpSession
from src.config import settings

from src.handers.autoposting import router as autoposting_router
from src.handers.moderation import router as moderation_router
from src.handers.admin import router as admin_router


def setup_handlers(dp: Dispatcher) -> None:
    dp.include_router(autoposting_router)
    dp.include_router(moderation_router)
    dp.include_router(admin_router)


def setup_middlewares(dp: Dispatcher) -> None:
    dp.update.outer_middleware(LoggingMiddleware())
    dp.message.middleware(DatabaseMiddleware())


async def setup_aiogram(dp: Dispatcher) -> None:
    setup_handlers(dp)
    setup_middlewares(dp)


async def setup_db(dp: Dispatcher):
    # engine = await init_db()
    # async_session = sessionmaker(
    #     bind=engine,
    #     class_=AsyncSession,
    #     expire_on_commit=False,
    #     autoflush=False,
    #     autocommit=False,
    # )
    # dp.workflow_data["engine"] = engine
    # dp.workflow_data["db_session"] = async_session

    db_manager = DatabaseManager(
        url=str(settings.db.url),
        echo=settings.db.echo,
        echo_pool=settings.db.echo_pool,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
    )
    dp.workflow_data["db_manager"]=db_manager


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_aiogram(dispatcher)
    await setup_db(dispatcher)
    logger.info("Bot started")


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.session.close()
    await dispatcher.storage.close()
    # await dp.workflow_data["engine"].dispose()
    await dispatcher.workflow_data["db_manager"].dispose()
    logger.info("Bot stopped")


def main() -> None:
    setup_logging(log_level="DEBUG", json_format=False)
    session1 = SmartAiohttpSession()
    bot = Bot(
        token=settings.run.token,
        session=session1,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)
    dp.startup.register(aiogram_on_startup_polling)
    dp.shutdown.register(aiogram_on_shutdown_polling)
    # example
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, db_session: AsyncSession):
        logger.info(f"Received message: {message.text}")
        async with db_session as session:
            user = await session.get(User, message.from_user.id)
            if not user:
                user = User(
                    id=message.from_user.id,
                    username=message.from_user.username,
                    role=UserRole.USER,
                )
                session.add(user)
                await session.commit()
        await message.answer(f"Welcome, {user.id}!")
        # await db_session.close()

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
