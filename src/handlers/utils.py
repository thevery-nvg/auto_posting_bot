from datetime import datetime
from typing import Optional

from aiogram import types
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import update_post, get_post_by_id, get_channel_by_id
from src.core.models import User, UserRole, Log, Post, PostStatus, Channel
from src.handlers.manage_posts.shedule import global_storage


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
    list_posts_types_text = "Списки постов"
    list_posts_types_callback = "#list_posts_types#"
    cancel_post_text = "Отменить пост"
    cancel_post_callback = "#cancel_post#"

    pending_posts_text = "Ожидающие публикации"
    pending_posts_callback = "#pending_posts#"
    published_posts_text = "Опубликованные посты"
    published_posts_callback = "#published_posts#"
    cancelled_posts_text = "Отмененные посты"
    cancelled_posts_callback = "#cancelled_posts#"
    publish_now_text = "Опубликовать сейчас"
    publish_now_callback = "#publish_now#"
    yes_sure_callback = "#yes_publish_now#"
    no_god_no_callback = "#no_publish_now#"

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


def go_to_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    return builder.as_markup()


def yes_no_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Да", callback_data=Buttons.yes_sure_callback),
        InlineKeyboardButton(text="Нет", callback_data=Buttons.no_god_no_callback),
    )
    return builder.as_markup()


class Admin(StatesGroup):
    main = State()
    manage_channels = State()
    manage_channels_change_name = State()
    manage_channels_change_notification = State()

    add_channel_name = State()
    add_channel_id = State()
    add_notification_id = State()
    change_moderation = State()
    end_add_channel = State()

    remove_channel = State()

    manage_posts = State()
    manage_posts_set_title = State()
    manage_posts_enter_text = State()
    manage_posts_media = State()
    manage_posts_set_time = State()
    manage_posts_switch_page = State()
    manage_posts_details = State()
    change_comment_chat_id= State()

    posts_list = State()
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
        text="Изменить чат комментариев",
        callback_data=f"change_comment_chat_id_{channel.id}",
    )
    builder.button(
        text="Изменить чат уведомлений",
        callback_data=f"change_chat_notification_{channel.id}",
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder


def get_post_details_text(post):
    if not post:
        return "❌ Информация о посте не найдена"

    status_emoji = {
        "pending": "⏳",
        "scheduled": "📅",
        "published": "✅",
        "failed": "❌",
        "draft": "📝",
    }

    status_text = {
        "pending": "ОЖИДАЕТ",
        "scheduled": "ЗАПЛАНИРОВАН",
        "published": "ОПУБЛИКОВАН",
        "failed": "ОШИБКА",
        "draft": "ЧЕРНОВИК",
    }

    status = post.status.value if hasattr(post.status, "value") else post.status
    status_display = f"{status_emoji.get(status, '❓')} <b>{status_text.get(status, status.upper())}</b>"

    media_type_emoji = {
        "photo": "🖼",
        "video": "🎬",
        "document": "📄",
        "audio": "🎵",
        "animation": "🎞",
        None: "📝",
    }

    media_type_display = (
        f"{media_type_emoji.get(post.media_type, '📎')} {post.media_type or 'Текст'}"
    )

    publish_time = (
        post.publish_time.strftime("%d.%m.%Y в %H:%M")
        if post.publish_time
        else "⏰ Не указано"
    )
    created_at = (
        post.created_at.strftime("%d.%m.%Y в %H:%M") if post.created_at else "—"
    )

    published_at = (
        post.published.strftime("%d.%m.%Y в %H:%M") if post.published else "—"
    )
    text_preview = (
        post.text[:100] + "..."
        if post.text and len(post.text) > 100
        else post.text or "❌ Нет текста"
    )
    title_preview = (
        post.title[:50] + "..."
        if post.title and len(post.title) > 50
        else post.title or "❌ Без заголовка"
    )

    return (
        f"<b>📝 Информация о посте</b>\n\n"
        f"<b>🆔 ID:</b> <code>{post.id}</code>\n"
        f"<b>🏷 Заголовок:</b> <code>{title_preview}</code>\n\n"
        f"<b>📄 Текст:</b>\n<code>{text_preview}</code>\n\n"
        f"<b>📊 Детали:</b>\n"
        f"  • <b>Тип контента:</b> {media_type_display}\n"
        f"  • <b>Медиа файл:</b> <code>{post.media_file_id or '❌ Нет медиа'}</code>\n"
        f"  • <b>Канал:</b> <code>{post.channel_id}</code>\n\n"
        f"<b>👤 Автор:</b> <code>{post.created_by}</code>\n"
        f"<b>📈 Статус:</b> {status_display}\n\n"
        f"<b>⏰ Время публикации:</b> <code>{publish_time}</code>\n"
        f"<b>📅 Создан:</b> <code>{created_at}</code>\n"
        f"<b>🔄 Опубликован:</b> <code>{published_at}</code>\n"
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
    if post.status != PostStatus.CANCELLED:
        builder.button(
            text=Buttons.cancel_post_text, callback_data=Buttons.cancel_post_callback
        )
    if post.status != PostStatus.PUBLISHED:
        builder.button(
            text=Buttons.publish_now_text, callback_data=Buttons.publish_now_callback
        )
    builder.button(**media_btn)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder


# Дополнительная функция для краткого отображения
def get_post_preview_text(post):
    if not post:
        return "❌ Пост не найден"

    status_emoji = {
        "pending": "⏳",
        "scheduled": "📅",
        "published": "✅",
        "failed": "❌",
        "draft": "📝",
    }

    status = post.status.value if hasattr(post.status, "value") else post.status
    title_preview = (
        post.title[:30] + "..."
        if post.title and len(post.title) > 30
        else post.title or "Без заголовка"
    )

    publish_time = (
        post.publish_time.strftime("%d.%m %H:%M") if post.publish_time else "—"
    )

    return (
        f"{status_emoji.get(status, '❓')} <b>Пост #{post.id}</b>\n"
        f"<code>{title_preview}</code>\n"
        f"📅 {publish_time} | 🏷 {status}\n"
        f"📺 Канал: <code>{post.channel_id}</code>"
    )


async def publish_post(post_id: int) -> None:
    bot = global_storage["bot"]
    db_manager = global_storage["db_manager"]
    session_generator = db_manager.get_async_session()
    async for session in session_generator:
        db_session = session
        post: Post = await get_post_by_id(db_session, post_id)
        channel: Channel = await get_channel_by_id(db_session, post.channel_id)
        data = {
            k: v
            for k, v in {
                "chat_id": post.channel_id,
                "photo": post.media_file_id if post.media_type == "photo" else None,
                "video": post.media_file_id if post.media_type == "video" else None,
                "document": post.media_file_id if post.media_type == "document" else None,
                "caption": post.text,
                "parse_mode": "Markdown",
            }.items()
            if v
        }
        msg: types.Message = await bot.send_document(**data)
        logger.info(f"Post ID:{post.id} is published in channel {channel.name}[{post.channel_id}]")
        if channel.notification_chat_id:
            await bot.send_message(
                chat_id=channel.notification_chat_id,
                text=f"Пост <b>{post.title}</b> опубликован в канале <b>{channel.name}[{post.channel_id}]</b>",
                parse_mode="HTML",
            )
        post.message_id = msg.message_id
        post.published = datetime.now()
        post.status = PostStatus.PUBLISHED
        await update_post(db_session, post)
