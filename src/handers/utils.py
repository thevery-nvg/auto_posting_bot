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

class Buttons:
    # Main menu
    manage_channels_text = "Управление каналами"
    manage_channels_callback = "manage_channels"

    manage_posts_text= "Управление постами"
    manage_posts_callback = "manage_posts"

    manage_moderator_text= "Управление модераторами"
    manage_moderator_callback = "manage_moderator"

    logs_text = "Просмотр логов"
    logs_callback = "view_logs"
    stats_text = "Статистика"
    stats_callback = "view_stats"
    # Manage channels
    add_channel_text = "Добавить канал"
    add_channel_callback = "add_channel"
    remove_channel_text = "Удалить канал (по ID)"
    remove_channel_callback = "remove_channel"
    list_channels_text = "Список каналов"
    list_channels_callback = "list_channels"
    # Manage moderator
    add_moderator_text = "Добавить модератора"
    add_moderator_callback = "add_moderator"
    remove_moderator_text = "Удалить модератора (по ID)"
    remove_moderator_callback = "remove_moderator"
    list_moderators_text = "Список модераторов"
    list_moderators_callback = "list_moderators"
    # Manage posts
    create_post_text = "Создать пост"
    create_post_callback = "add_post"
    remove_post_text = "Удалить пост (по ID)"
    remove_post_callback = "remove_post"
    list_posts_text = "Список постов"
    list_posts_callback = "list_posts"
    skip_media_text = "Пропустить"
    skip_media_callback = "skip_media"

    forward_text = "Вперед"
    forward_callback = "#forward#"
    back_text = "Назад"
    back_callback = "#back#"
    goto_main_text = "Главное меню"
    goto_main_callback = "#main_menu#"


goto_main_menu_btn = {
    "text": Buttons.goto_main_text,
    "callback_data": Buttons.goto_main_callback,
}

class Admin(StatesGroup):
    main = State()
    manage_channels = State()
    manage_channels_change_name = State()
    manage_channels_change_notification = State()
    manage_posts = State()
    manage_posts_enter_text = State()
    manage_posts_media= State()
    manage_posts_set_time= State()

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
