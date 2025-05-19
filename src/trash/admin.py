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


# Определяем FSM для добавления канала
class AddChannel(StatesGroup):
    enter_id = State()
    enter_name = State()
    enter_chat_id = State()


# Определяем FSM для добавления модератора
class AddModerator(StatesGroup):
    enter_id = State()


async def check_admin_access(
    user_id: int,
    db_session: AsyncSession,
    message: Optional[types.Message] = None,
    callback: Optional[types.CallbackQuery] = None
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
    db_session: AsyncSession,
    user_id: int,
    action: str,
    details: str
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


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, db_session: AsyncSession):
    if not await check_admin_access(message.from_user.id, db_session):
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Управление модераторами", callback_data="manage_moderators")
    builder.button(text="Управление каналами", callback_data="manage_channels")
    builder.button(text="Статистика", callback_data="view_stats")
    builder.button(text="Логи", callback_data="view_logs")
    builder.adjust(1)

    await message.answer("Админ-панель:", reply_markup=builder.as_markup())




@router.callback_query(F.data == "manage_channels")
async def manage_channels(callback: types.CallbackQuery, db_session: AsyncSession):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить канал", callback_data="add_channel")
    builder.button(text="Удалить канал", callback_data="remove_channel")
    builder.button(text="Список каналов", callback_data="list_channels")
    builder.adjust(1)

    await callback.message.edit_text(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "add_channel")
async def start_add_channel(
    callback: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    await callback.message.answer(
        "Введите Telegram ID канала (например, -100123456789):"
    )
    await state.set_state(AddChannel.enter_id)
    await callback.answer()


@router.message(AddChannel.enter_id)
async def process_channel_id(message: types.Message, state: FSMContext):
    try:
        channel_id = int(message.text)
    except ValueError:
        await message.answer("Неверный формат ID. Введите числовой Telegram ID.")
        return

    await state.update_data(channel_id=channel_id)
    await message.answer("Введите название канала:")
    await state.set_state(AddChannel.enter_name)


@router.message(AddChannel.enter_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название канала не может быть пустым.")
        return

    await state.update_data(name=name)
    await message.answer(
        "Введите Telegram ID чата для уведомлений (или '-' для пропуска):"
    )
    await state.set_state(AddChannel.enter_chat_id)


@router.message(AddChannel.enter_chat_id)
async def process_chat_id(
    message: types.Message, state: FSMContext, db_session: AsyncSession, bot: Bot
):
    data = await state.get_data()
    channel_id = data["channel_id"]
    name = data["name"]
    chat_id = None if message.text == "-" else message.text

    if chat_id and not chat_id.isdigit():
        await message.answer("Неверный формат ID чата. Введите числовой ID или '-'.")
        return
    chat_id = int(chat_id) if chat_id else None

    try:
        chat_admins = await bot.get_chat_administrators(channel_id)
        bot_id = (await bot.get_me()).id
        if not any(admin.user.id == bot_id for admin in chat_admins):
            await message.answer("Бот должен быть администратором в канале.")
            await state.clear()
            return
    except Exception as e:
        await message.answer(f"Ошибка проверки канала: {str(e)}")
        await state.clear()
        return

    async with db_session.begin():
        channel = Channel(
            id=channel_id,
            name=name,
            notification_chat_id=chat_id,
            is_active=True,
            moderation_enabled=True,
        )
        db_session.add(channel)
        await log_action(
            db_session,
            message.from_user.id,
            "add_channel",
            f"Channel: {channel_id}, Name: {name}"
        )

    await message.answer(f"Канал {name} добавлен.")
    await state.clear()


@router.callback_query(F.data == "remove_channel")
async def start_remove_channel(callback: types.CallbackQuery, db_session: AsyncSession):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    async with db_session.begin():
        result = await db_session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await callback.message.answer("Нет активных каналов.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=channel.name, callback_data=f"remove_channel_{channel.id}")
    builder.adjust(1)

    await callback.message.edit_text(
        "Выберите канал для удаления:", reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_channel_"))
async def confirm_remove_channel(
    callback: types.CallbackQuery, db_session: AsyncSession
):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    channel_id = int(callback.data.split("_")[2])
    async with db_session.begin():
        channel = await db_session.get(Channel, channel_id)
        if not channel:
            await callback.message.answer("Канал не найден.")
            await callback.answer()
            return

        channel.is_active = False
        await log_action(
            db_session,
            callback.from_user.id,
            "remove_channel",
            f"Channel: {channel_id}"
        )

    await callback.message.answer(f"Канал {channel.name} удален.")
    await callback.answer()


@router.callback_query(F.data == "list_channels")
async def list_channels(callback: types.CallbackQuery, db_session: AsyncSession):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    async with db_session.begin():
        result = await db_session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await callback.message.answer("Нет активных каналов.")
        await callback.answer()
        return

    text = "Список каналов:\n" + "\n".join(
        [f"ID: {ch.id}, Name: {ch.name}" for ch in channels]
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "view_stats")
async def view_stats(callback: types.CallbackQuery, db_session: AsyncSession):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Показать статистику", callback_data="show_stats")
    builder.button(text="Экспортировать в CSV", callback_data="export_stats")
    builder.adjust(1)

    await callback.message.edit_text("Статистика:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "show_stats")
async def show_stats(callback: types.CallbackQuery, db_session: AsyncSession):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    async with db_session.begin():
        result = await db_session.execute(
            select(Stat).join(Channel).filter(Channel.is_active == True)
        )
        stats = result.scalars().all()

    if not stats:
        await callback.message.answer("Нет данных для статистики.")
        await callback.answer()
        return

    text = "Статистика по каналам:\n"
    for stat in stats:
        channel = await db_session.get(Channel, stat.channel_id)
        text += (
            f"Канал: {channel.name if channel else 'N/A'}, "
            f"Пост ID: {stat.post_id or 'N/A'}, "
            f"Просмотры: {stat.views}, "
            f"Комментарии: {stat.comments}\n"
        )

    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "export_stats")
async def export_stats(
    callback: types.CallbackQuery, db_session: AsyncSession, bot: Bot
):
    if not await check_admin_access(callback.from_user.id, db_session, callback=callback):
        return

    async with db_session.begin():
        result = await db_session.execute(
            select(Stat).join(Channel).filter(Channel.is_active == True)
        )
        stats = result.scalars().all()

    if not stats:
        await callback.message.answer("Нет данных для экспорта.")
        await callback.answer()
        return

    data = []
    async with db_session.begin():
        for stat in stats:
            channel = await db_session.get(Channel, stat.channel_id)
            data.append({
                "channel_id": stat.channel_id,
                "channel_name": channel.name if channel else "N/A",
                "post_id": stat.post_id,
                "views": stat.views,
                "comments": stat.comments,
                "timestamp": stat.timestamp.strftime("%Y-%m-%d %H:%M"),
            })

    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_file = types.BufferedInputFile(
        csv_buffer.getvalue().encode(), filename="stats.csv"
    )

    await bot.send_document(callback.message.chat.id, csv_file)
    await callback.answer()


@router.message(Command("logs"))
async def cmd_logs(message: types.Message, db_session: AsyncSession):
    if not await check_admin_access(message.from_user.id, db_session, message=message):
        return

    async with db_session.begin():
        result = await db_session.execute(
            select(Log)
            .join(User, Log.user_id == User.id)
            .order_by(Log.timestamp.desc())
            .limit(50)
        )
        logs = result.scalars().all()

    if not logs:
        await message.answer("Нет логов.")
        return

    text = "Последние логи:\n"
    for log in logs:
        text += (
            f"[{log.timestamp.strftime('%Y-%m-%d %H:%M')}] "
            f"{log.action} by @{log.user.username or log.user_id}: "
            f"{log.details}\n"
        )

    await message.answer(text[:4000])  # Ограничение длины сообщения в Telegram