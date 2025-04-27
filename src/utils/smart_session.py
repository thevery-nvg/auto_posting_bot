import asyncio
import time
from typing import Any, Optional, Dict

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    RestartingTelegram,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods.base import TelegramMethod, TelegramType
from loguru import logger


class SmartAiohttpSession(AiohttpSession):
    """Умная сессия с логированием и обработкой ошибок"""

    def _serialize_response(self, response: Any) -> Dict[str, Any]:
        """Безопасная сериализация ответа для логов"""
        if hasattr(response, "model_dump"):
            try:
                return response.model_dump(exclude_none=True)
            except Exception:
                return {"response": str(response)}
        return {"response": str(response)}

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: Optional[int] = None,
    ) -> TelegramType:
        context_logger = logger.bind(
            api_method=method.__api_method__,
            bot_token=bot.token[-6:],  # Логируем только последние 6 символов токена
            timeout=timeout,
        )

        start_time = time.monotonic()
        attempt = 0

        while True:
            attempt += 1
            try:
                context_logger.debug("Making API request (attempt {})", attempt)

                result = await super().make_request(bot, method, timeout)

                # Логируем успешный запрос
                context_logger.debug(
                    "API request successful",
                    response=self._serialize_response(result),
                    duration_ms=round((time.monotonic() - start_time) * 1000, 2),
                )

                return result

            except TelegramRetryAfter as e:
                wait_time = e.retry_after
                context_logger.warning(
                    "Rate limit exceeded, retrying after {} seconds",
                    wait_time,
                )
                await asyncio.sleep(wait_time)

            except (RestartingTelegram, TelegramServerError) as e:
                if attempt > 6:
                    wait_time = 1000
                else:
                    wait_time = 2**attempt

                context_logger.warning(
                    "Telegram server error ({}), retrying in {} seconds",
                    str(e),
                    wait_time,
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                context_logger
