import asyncio

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from core.database import DatabaseManager
from src.config import settings
from src.middlewares.db_middleware import DatabaseMiddleware
from src.middlewares.logging_middleware import LoggingMiddleware
from src.utils.logger import setup_logging
from src.utils.smart_session import SmartAiohttpSession


def setup_handlers(dp: Dispatcher) -> None:
    from src.handlers.admin import router as admin_router
    from src.handlers.manage_posts.posts_main import router as post_manage_router
    from src.handlers.manage_channels.channels_main import (
        router as channel_manage_router,
    )
    from src.handlers.common import router as common_router

    dp.include_router(admin_router)
    dp.include_router(channel_manage_router)
    dp.include_router(post_manage_router)
    dp.include_router(common_router)


def setup_middlewares(dp: Dispatcher) -> None:
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.middleware(LoggingMiddleware())


async def setup_aiogram(dp: Dispatcher) -> None:
    setup_db(dp)
    setup_middlewares(dp)
    setup_handlers(dp)


def setup_db(dispatcher: Dispatcher) -> None:
    try:
        db_manager = DatabaseManager(
            url=str(settings.db.url),
            echo=settings.db.echo,
            echo_pool=settings.db.echo_pool,
            pool_size=settings.db.pool_size,
            max_overflow=settings.db.max_overflow,
        )
        dispatcher.workflow_data["db_manager"] = db_manager
        logger.info("DB connect successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_aiogram(dispatcher)
    logger.info("Bot started successfully")


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await dispatcher.storage.close()
    await dispatcher.workflow_data["db_manager"].dispose()
    logger.info("DB connection closed")
    await bot.session.close()
    logger.info("Bot stopping successful")


def main() -> None:
    setup_logging(log_level="DEBUG", json_format=False)
    smart_session = SmartAiohttpSession()
    bot = Bot(
        token=settings.run.token,
        session=smart_session,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)
    dp.startup.register(aiogram_on_startup_polling)
    dp.shutdown.register(aiogram_on_shutdown_polling)

    asyncio.run(dp.start_polling(bot))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard")
