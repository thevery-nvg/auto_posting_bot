import pandas as pd
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from io import StringIO
from typing import Optional

from src.core.models import User, UserRole, Channel, Stat, Log

router = Router(name="admin")


async def check_admin_access(
    user_id: int,
    db_session: AsyncSession,
    message: Optional[types.Message] = None,
    callback: Optional[types.CallbackQuery] = None,
) -> bool:
    """Проверка прав администратора с отправкой сообщения об ошибке"""
    is_admin = await is_user_admin(user_id, db_session)
    if not is_admin:
        error_msg = "Доступ только для администраторов."
        if message:
            await message.answer(error_msg)
        elif callback:
            await callback.message.answer(error_msg)
    return is_admin


async def is_user_admin(user_id: int, db_session: AsyncSession) -> bool:
    """Проверяет, является ли пользователь администратором"""
    async with db_session.begin():
        user = await db_session.get(User, user_id)
        return user and user.role == UserRole.ADMIN


async def log_action(
    db_session: AsyncSession, user_id: int, action: str, details: str
) -> None:
    """Логирование действий администратора"""
    log = Log(
        user_id=user_id,
        action=action,
        details=details,
        timestamp=datetime.now(),
    )
    db_session.add(log)
    await db_session.commit()
