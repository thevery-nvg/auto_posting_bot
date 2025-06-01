import asyncio
import tenacity
from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from core.database import init_db
from src.middlewares.logging_middleware import LoggingMiddleware
from src.middlewares.db_middleware import DatabaseMiddleware
from src.utils.logger import setup_logging
from src.utils.smart_session import SmartAiohttpSession
from src.config import settings



def setup_handlers(dp: Dispatcher) -> None:
    from src.handers.admin import router as admin_router
    from src.handers.manage_posts.posts_main import router as post_manage_router
    from src.handers.manage_channels.channels_main import router as channel_manage_router
    dp.include_router(admin_router)
    dp.include_router(channel_manage_router)
    dp.include_router(post_manage_router)


def setup_middlewares(dp: Dispatcher) -> None:
    dp.update.outer_middleware(LoggingMiddleware())
    #dp.update.middleware(DatabaseMiddleware())


async def setup_aiogram(dp: Dispatcher) -> None:
    setup_handlers(dp)
    setup_middlewares(dp)


async def setup_db(dispatcher: Dispatcher) -> None:
    try:
        engine, session_factory = await init_db()
        dispatcher.workflow_data["engine"] = engine
        dispatcher.workflow_data["session_factory"] = session_factory
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_aiogram(dispatcher)
    #await setup_db(dispatcher)
    logger.info("Bot started")


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.session.close()
    await dispatcher.storage.close()
    #await dispatcher.workflow_data["engine"].dispose()
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
