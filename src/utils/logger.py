from loguru import logger
import sys
import json
from datetime import datetime


def serialize_record(record):
    """Сериализация записи лога для JSON формата"""

    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return str(obj)
        return str(obj)

    return {
        "time": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "extra": {k: default_serializer(v) for k, v in record["extra"].items()},
    }


def setup_logging(log_level: str = "INFO", json_format: bool = False):
    """Настройка логгера loguru"""

    logger.remove()

    # Простой текстовый формат
    text_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Форматтер для JSON
    def json_formatter(record):
        record["extra"]["serialized"] = serialize_record(record)
        return json.dumps(record["extra"]["serialized"])

    # Добавляем консольный вывод
    logger.add(
        sys.stdout,
        level=log_level,
        format=json_formatter if json_format else text_format,
        colorize=not json_format,
        backtrace=True,
        diagnose=True,
        serialize=False,  # Отключаем встроенную сериализацию
    )

    return logger
