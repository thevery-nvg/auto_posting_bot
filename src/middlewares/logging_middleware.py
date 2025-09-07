import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих обновлений"""
    @staticmethod
    def _serialize_chat_member(member) -> Dict[str, Any]|None:
        """Сериализация информации об участнике чата"""
        if member is None:
            return None
        return {
            "status": member.status,
            "user_id": getattr(member.user, "id", None),
            "is_chat_member": getattr(member, "is_chat_member", None),
        }

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        start_time = time.monotonic()
        context_logger = logger.bind(update_id=event.update_id)

        # Логируем входящее обновление
        self._log_incoming_update(event, context_logger)

        try:
            result = await handler(event, data)

            # Логируем успешную обработку
            duration = round((time.monotonic() - start_time) * 1000, 2)
            context_logger.info(
                "Update processed successfully",
                duration_ms=duration,
            )

            return result

        except Exception as e:
            # Логируем ошибку
            duration = round((time.monotonic() - start_time) * 1000, 2)
            context_logger.error(
                "Error processing update",
                error=str(e),
                duration_ms=duration,
            )
            raise

    def _log_incoming_update(self, event: Update, logger):
        """Логирование входящего обновления"""
        if event.message:
            self._log_message(event.message, logger)
        elif event.callback_query:
            self._log_callback_query(event.callback_query, logger)
        elif event.inline_query:
            self._log_inline_query(event.inline_query, logger)
        elif event.my_chat_member:
            self._log_chat_member_update(event.my_chat_member, "my_chat_member", logger)
        elif event.chat_member:
            self._log_chat_member_update(event.chat_member, "chat_member", logger)
    @staticmethod
    def _log_message(message, logger):
        """Логирование входящего сообщения"""
        log_context = {
            "update_type": "message",
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type,
        }

        if message.from_user:
            log_context["user_id"] = message.from_user.id

        if message.text:
            log_context["text"] = message.text[:200]  # Ограничиваем длину текста

        logger.bind(**log_context).debug(f"Received message {message.text} from {message.from_user.id} MIDDLEWARE")

    @staticmethod
    def _log_callback_query(callback_query, logger):
        """Логирование callback query"""
        log_context = {
            "update_type": "callback_query",
            "callback_id": callback_query.id,
            "data": callback_query.data[:100],  # Ограничиваем длину данных
            "user_id": callback_query.from_user.id,
        }

        if callback_query.message:
            log_context.update(
                {
                    "message_id": callback_query.message.message_id,
                    "chat_id": callback_query.message.chat.id,
                }
            )

        logger.bind(**log_context).debug("Received callback query")

    @staticmethod
    def _log_inline_query(inline_query, logger):
        """Логирование inline query"""
        logger.bind(
            update_type="inline_query",
            query_id=inline_query.id,
            user_id=inline_query.from_user.id,
            query=inline_query.query[:100],  # Ограничиваем длину запроса
        ).debug("Received inline query")

    def _log_chat_member_update(self, update, update_type, logger):
        """Логирование изменений статуса участника чата"""
        logger.bind(
            update_type=update_type,
            user_id=update.from_user.id,
            chat_id=update.chat.id,
            old_status=self._serialize_chat_member(update.old_chat_member),
            new_status=self._serialize_chat_member(update.new_chat_member),
        ).debug(f"Received {update_type} update")
