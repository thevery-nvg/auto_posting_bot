import asyncio
import time
from contextlib import contextmanager
from typing import Any, Optional, Dict, TypeVar, Union,Generator

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import (
    RestartingTelegram,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.methods.base import TelegramMethod, TelegramType
from loguru import logger

TelegramTypeT = TypeVar("TelegramTypeT", bound=TelegramType)


class SmartAiohttpSession(AiohttpSession):
    """Умная сессия с расширенным логированием, обработкой ошибок и retry-логикой"""

    def __init__(
        self,
        max_attempts: int = 6,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        **kwargs: Any,
    ):
        """
        :param max_attempts: Максимальное количество попыток выполнения запроса
        :param base_delay: Базовое время ожидания между попытками (секунды)
        :param max_delay: Максимальное время ожидания между попытками (секунды)
        """
        super().__init__(**kwargs)
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    @staticmethod
    def _serialize_response(response: Any) -> Dict[str, Any]:
        """Безопасная сериализация ответа для логов"""
        if hasattr(response, "model_dump"):
            try:
                return response.model_dump(exclude_none=True)
            except Exception:
                return {"response": str(response)}
        return {"response": str(response)}

    @contextmanager
    def _measure_time(self):
        """Контекстный менеджер для измерения времени выполнения"""
        start_time = time.monotonic()
        yield lambda: time.monotonic() - start_time

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramTypeT],
        timeout: Optional[int] = None,
    ) -> TelegramTypeT:
        """
        Выполняет запрос к Telegram API с обработкой ошибок и повторными попытками

        :param bot: Экземпляр бота
        :param method: Метод Telegram API
        :param timeout: Таймаут запроса
        :return: Результат выполнения метода
        :raises: Исключения Telegram API после исчерпания попыток
        """
        context_logger = logger.bind(
            api_method=method.__api_method__,
            bot_token=bot.token[-6:],  # Логируем только последние 6 символов токена
            timeout=timeout,
        )

        with self._measure_time() as get_duration:
            attempt = 0
            last_error: Optional[Exception] = None

            while attempt < self.max_attempts:
                attempt += 1
                try:
                    context_logger.debug(
                        "Making API request (attempt {}/{})", attempt, self.max_attempts
                    )

                    result = await super().make_request(bot, method, timeout)

                    context_logger.debug(
                        "API request successful",
                        response=self._serialize_response(result),
                        duration_ms=round(get_duration() * 1000, 2),
                    )

                    return result

                except TelegramRetryAfter as e:
                    wait_time = min(e.retry_after, self.max_delay)
                    context_logger.warning(
                        "Rate limit exceeded, retrying after {} seconds (attempt {}/{})",
                        wait_time,
                        attempt,
                        self.max_attempts,
                    )
                    await asyncio.sleep(wait_time)
                    last_error = e

                except (RestartingTelegram, TelegramServerError) as e:
                    wait_time = min(
                        self.base_delay * (2 ** (attempt - 1)), self.max_delay
                    )
                    context_logger.warning(
                        "Telegram server error ({}), retrying in {} seconds (attempt {}/{})",
                        str(e),
                        wait_time,
                        attempt,
                        self.max_attempts,
                    )
                    await asyncio.sleep(wait_time)
                    last_error = e

                except Exception as e:
                    context_logger.error(
                        "Unexpected error during API request (attempt {}/{}): {}",
                        attempt,
                        self.max_attempts,
                        str(e),
                        exc_info=e,
                    )
                    last_error = e
                    break

            # Если сюда дошли, значит все попытки исчерпаны или произошла непредвиденная ошибка
            context_logger.error(
                "API request failed after {} attempts, last error: {}",
                attempt,
                str(last_error) if last_error else "unknown",
                duration_ms=round(get_duration() * 1000, 2),
            )

            if last_error:
                raise last_error
            raise RuntimeError("API request failed with unknown error")
