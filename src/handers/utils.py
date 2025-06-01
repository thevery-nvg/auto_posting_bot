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

from src.core.models import User, UserRole, Channel, Stat, Log, Post


class Buttons:
    # Main menu
    manage_channels_text = "Управление каналами"
    manage_channels_callback = "#manage_channels#"

    manage_posts_text = "Управление постами"
    manage_posts_callback = "#manage_posts#"

    manage_moderator_text = "Управление модераторами"
    manage_moderator_callback = "#manage_moderator#"

    logs_text = "Просмотр логов"
    logs_callback = "#view_logs#"
    stats_text = "Статистика"
    stats_callback = "#view_stats#"
    # Manage channels
    add_channel_text = "Добавить канал"
    add_channel_callback = "#add_channel#"
    remove_channel_text = "Удалить канал (по ID)"
    remove_channel_callback = "#remove_channel#"
    list_types_text = "Типы каналов"
    list_types_callback = "#list_types#"
    list_channels_text = "Список каналов"
    list_channels_callback = "#list_channels#"
    all_channels_text = "Все каналы"
    all_channels_callback = "#all_channels#"
    active_channels_text = "Активные каналы"
    active_channels_callback = "#active_channels#"
    inactive_channels_text = "Неактивные каналы"
    inactive_channels_callback = "#inactive_channels#"
    # Manage moderator
    add_moderator_text = "Добавить модератора"
    add_moderator_callback = "#add_moderator#"
    remove_moderator_text = "Удалить модератора (по ID)"
    remove_moderator_callback = "#remove_moderator#"
    list_moderators_text = "Список модераторов"
    list_moderators_callback = "#list_moderators#"
    # Manage posts
    create_post_text = "Создать пост"
    create_post_callback = "#add_post#"
    remove_post_text = "Удалить пост (по ID)"
    remove_post_callback = "#remove_post#"
    list_posts_text = "Список постов"
    list_posts_callback = "#list_posts#"
    skip_media_text = "Пропустить"
    skip_media_callback = "#skip_media#"
    # Post menu
    edit_text = "Редактировать текст"
    edit_callback = "#edit#"
    edit_title_text = "Редактировать заголовок"
    edit_title_callback = "#edit_title#"
    edit_time_text = "Изменить время публикации"
    edit_time_callback = "#edit_time#"
    edit_add_media_text = "Добавить медиа"
    edit_add_media_callback = "#add_media#"
    edit_remove_media_text = "Удалить медиа"
    edit_remove_media_callback = "#remove_media#"
    edit_channel_text = "Изменить канал"
    edit_channel_callback = "#edit_channel#"

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

    add_channel_name = State()
    add_channel_id = State()
    add_notification_id = State()

    remove_channel = State()

    manage_posts = State()
    manage_posts_set_title = State()
    manage_posts_enter_text = State()
    manage_posts_media = State()
    manage_posts_set_time = State()
    manage_posts_switch_page = State()

    edit_post_text = State()
    edit_post_time = State()
    edit_post_media = State()
    edit_post_title = State()

    remove_post = State()


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


def get_channel_details_text(channel):
    if not channel:
        return "No details"
    return (
        f"<b>📢 Информация о канале</b>\n\n"
        f"<b>🆔 ID:</b> <code>{channel.id}</code>\n"
        f"<b>🏷 Название:</b> <code>{channel.name}</code>\n\n"
        f"<b>⚙️ Настройки:</b>\n"
        f"  • <b>Статус:</b> {'<b><u>✅ АКТИВЕН</u></b>' if channel.is_active else '❌ неактивен'}\n"
        f"  • <b>Модерация:</b> {'<b><u>✅ ВКЛЮЧЕНА</u></b>' if channel.moderation_enabled else '❌ отключена'}\n"
        f"  • <b>Уведомления:</b> <code>{channel.notification_chat_id or '❌ не настроены'}</code>\n\n"
        f"<b>📅 Даты:</b>\n"
        f"  • <b>Создан:</b> <code>{channel.created_at}</code>\n"
        f"  • <b>Обновлен:</b> <code>{channel.updated_at}</code>\n"
    )


def get_channel_details_keyboard(channel):
    builder = InlineKeyboardBuilder()
    if not channel:
        builder.button(**goto_main_menu_btn)
        builder.adjust(1)
        return builder
    builder.button(text="Изменить имя", callback_data=f"change_name_{channel.id}")
    builder.button(
        text="Отключить" if channel.is_active else "Включить",
        callback_data=f"switch_channel_status_{channel.id}",
    )
    builder.button(
        text=(
            "Отключить модерацию"
            if channel.moderation_enabled
            else "Включить модерацию"
        ),
        callback_data=f"switch_moderation_status_{channel.id}",
    )
    builder.button(
        text="Изменить чат уведомлений",
        callback_data=f"change_chat_notification_{channel.id}",
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder


def get_post_details(post):
    return (
        f"📢 Пост ID:{post.id}:\n\n"
        f"Заголовок: {post.title}\n\n"
        f"Текст:{post.text}\n\n"
        f"Медиа тип: {post.media_type}\n\n"
        f"Медиа файл: {post.media_file_id}\n\n"
        f"Создано пользователем: {post.created_by}\n\n"
        f"Канал: {post.channel_id}\n\n"
        f"Статус: {post.status}\n\n"
        f"Время публикации: {post.publish_time.strftime('%Y-%m-%d %H:%M')}"
    )


def get_post_details_keyboard(post):
    builder = InlineKeyboardBuilder()
    media_btn = (
        {
            "text": Buttons.edit_add_media_text,
            "callback_data": Buttons.edit_add_media_callback,
        }
        if not post.media_type
        else {
            "text": Buttons.edit_remove_media_text,
            "callback_data": Buttons.edit_remove_media_callback,
        }
    )
    builder.button(
        text=Buttons.edit_title_text, callback_data=Buttons.edit_title_callback
    )
    builder.button(text=Buttons.edit_text, callback_data=Buttons.edit_callback)
    builder.button(
        text=Buttons.edit_channel_text, callback_data=Buttons.edit_channel_callback
    )
    builder.button(
        text=Buttons.edit_time_text, callback_data=Buttons.edit_time_callback
    )
    builder.button(**media_btn)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder


async def publish_post(bot: Bot, post: Post):
    try:
        if post.media_file_id and post.media_type:
            if post.media_type == "photo":
                await bot.send_photo(
                    chat_id=post.channel_id,
                    photo=post.media_file_id,
                    caption=post.text,
                    parse_mode="Markdown",
                )
            elif post.media_type == "video":
                await bot.send_video(
                    chat_id=post.channel_id,
                    video=post.media_file_id,
                    caption=post.text,
                    parse_mode="Markdown",
                )
            elif post.media_type == "document":
                await bot.send_document(
                    chat_id=post.channel_id,
                    document=post.media_file_id,
                    caption=post.text,
                    parse_mode="Markdown",
                )
        else:
            await bot.send_message(
                chat_id=post.channel_id, text=post.text, parse_mode="Markdown"
            )
    except Exception as e:
        print(e)
