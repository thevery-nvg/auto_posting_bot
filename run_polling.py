import asyncio

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger

from src.middlewares.logging_middleware import LoggingMiddleware
from src.utils.logger import setup_logging
from src.utils.smart_session import SmartAiohttpSession
from src.config import settings


def setup_handlers(dp: Dispatcher) -> None:
    pass


def setup_middlewares(dp: Dispatcher) -> None:
    dp.update.outer_middleware(LoggingMiddleware())


async def setup_aiogram(dp: Dispatcher) -> None:
    setup_handlers(dp)
    setup_middlewares(dp)


async def aiogram_on_startup_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await setup_aiogram(dispatcher)
    logger.info("Bot started")


async def aiogram_on_shutdown_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    await bot.session.close()
    await dispatcher.storage.close()
    logger.info("Bot stopped")


def main() -> None:
    setup_logging(log_level="DEBUG", json_format=False)
    session = SmartAiohttpSession()
    bot = Bot(
        token=settings.run.token,
        session=session,
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
        logger.info("Bot stopped by keyboard interrupt")
