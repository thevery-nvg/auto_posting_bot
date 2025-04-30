import pandas as pd
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import DatabaseManager
from src.core.models import User, UserRole, Channel, Stat, Log
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from io import StringIO

router = Router()


# Определяем FSM для добавления канала
class AddChannel(StatesGroup):
    enter_id = State()
    enter_name = State()
    enter_chat_id = State()


# Определяем FSM для добавления модератора
class AddModerator(StatesGroup):
    enter_id = State()


# Функция для проверки прав админа
async def is_admin(user_id: int, db_session: AsyncSession) -> bool:
    async with db_session as session:
        user = await session.get(User, user_id)
        return user and user.role == UserRole.ADMIN


# Главное меню админ-панели
@router.message(Command("admin"))
async def cmd_admin(message: types.Message, db_manager: DatabaseManager):
    db_session=db_manager.get_async_session()
    if not await is_admin(message.from_user.id, db_session):
        await message.answer("Доступ только для администраторов.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Управление модераторами", callback_data="manage_moderators")
    builder.button(text="Управление каналами", callback_data="manage_channels")
    builder.button(text="Статистика", callback_data="view_stats")
    builder.button(text="Логи", callback_data="view_logs")
    builder.adjust(1)

    await message.answer("Админ-панель:", reply_markup=builder.as_markup())


# Хендлер для управления модераторами
@router.callback_query(F.data == "manage_moderators")
async def manage_moderators(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить модератора", callback_data="add_moderator")
    builder.button(text="Удалить модератора", callback_data="remove_moderator")
    builder.button(text="Список модераторов", callback_data="list_moderators")
    builder.adjust(1)

    await callback.message.answer(
        "Управление модераторами:", reply_markup=builder.as_markup()
    )
    await callback.answer()


# Хендлер для добавления модератора
@router.callback_query(F.data == "add_moderator")
async def start_add_moderator(
    callback: types.CallbackQuery, state: FSMContext, db_manager: DatabaseManager
):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    await callback.message.answer(
        "Введите Telegram ID пользователя для назначения модератором:"
    )
    await state.set_state(AddModerator.enter_id)
    await callback.answer()


# Хендлер для ввода ID модератора
@router.message(AddModerator.enter_id)
async def process_add_moderator(
    message: types.Message, state: FSMContext, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("Неверный формат ID. Введите числовой Telegram ID.")
        return

    async with db_session as session:
        user = await session.get(User, user_id)
        if not user:
            user = User(id=user_id, role=UserRole.USER)
            session.add(user)

        if user.role == UserRole.ADMIN:
            await message.answer("Нельзя изменить роль администратора.")
            await state.clear()
            return

        user.role = UserRole.MODERATOR
        session.add(user)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="add_moderator",
            details=f"User: {user_id}",
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

    await message.answer(f"Пользователь {user_id} назначен модератором.")
    await state.clear()


# Хендлер для удаления модератора
@router.callback_query(F.data == "remove_moderator")
async def start_remove_moderator(
    callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(select(User).filter_by(role=UserRole.MODERATOR))
        moderators = result.scalars().all()

    if not moderators:
        await callback.message.answer("Нет модераторов для удаления.")
        return

    builder = InlineKeyboardBuilder()
    for mod in moderators:
        builder.button(text=f"ID: {mod.id}", callback_data=f"remove_mod_{mod.id}")
    builder.adjust(1)

    await callback.message.answer(
        "Выберите модератора для удаления:", reply_markup=builder.as_markup()
    )
    await callback.answer()


# Хендлер для подтверждения удаления модератора
@router.callback_query(F.data.startswith("remove_mod_"))
async def confirm_remove_moderator(
    callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    user_id = int(callback.data.split("_")[2])
    async with db_session as session:
        user = await session.get(User, user_id)
        if not user or user.role != UserRole.MODERATOR:
            await callback.message.answer("Модератор не найден.")
            return

        user.role = UserRole.USER
        session.add(user)

        # Логируем действие
        log = Log(
            user_id=callback.from_user.id,
            action="remove_moderator",
            details=f"User: {user_id}",
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

    await callback.message.answer(f"Пользователь {user_id} больше не модератор.")
    await callback.answer()


# Хендлер для списка модераторов
@router.callback_query(F.data == "list_moderators")
async def list_moderators(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(select(User).filter_by(role=UserRole.MODERATOR))
        moderators = result.scalars().all()

    if not moderators:
        await callback.message.answer("Нет модераторов.")
        return

    text = "Список модераторов:\n" + "\n".join(
        [f"ID: {mod.id}, Username: @{mod.username or 'N/A'}" for mod in moderators]
    )
    await callback.message.answer(text)
    await callback.answer()


# Хендлер для управления каналами
@router.callback_query(F.data == "manage_channels")
async def manage_channels(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить канал", callback_data="add_channel")
    builder.button(text="Удалить канал", callback_data="remove_channel")
    builder.button(text="Список каналов", callback_data="list_channels")
    builder.adjust(1)

    await callback.message.answer(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await callback.answer()


# Хендлер для добавления канала
@router.callback_query(F.data == "add_channel")
async def start_add_channel(
    callback: types.CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    await callback.message.answer(
        "Введите Telegram ID канала (например, -100123456789):"
    )
    await state.set_state(AddChannel.enter_id)
    await callback.answer()


# Хендлер для ввода ID канала
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


# Хендлер для ввода названия канала
@router.message(AddChannel.enter_name)
async def process_channel_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer(
        "Введите Telegram ID чата для уведомлений (или '-' для пропуска):"
    )
    await state.set_state(AddChannel.enter_chat_id)


# Хендлер для ввода ID чата
@router.message(AddChannel.enter_chat_id)
async def process_chat_id(
    message: types.Message, state: FSMContext, db_manager: DatabaseManager, bot:Bot):
    db_session = db_manager.get_async_session()
    data = await state.get_data()
    channel_id = data["channel_id"]
    name = data["name"]
    chat_id = None if message.text == "-" else int(message.text)

    # Проверяем, является ли бот админом в канале
    try:
        chat_admins = await bot.get_chat_administrators(channel_id)
        bot_id = (await bot.get_me()).id
        if not any(admin.user.id == bot_id for admin in chat_admins):
            await message.answer("Бот должен быть администратором в канале.")
            await state.clear()
            return
    except Exception as e:
        await message.answer(f"Ошибка проверки канала: {e}")
        await state.clear()
        return

    async with db_session as session:
        channel = Channel(
            id=channel_id,
            name=name,
            notification_chat_id=chat_id,
            is_active=True,
            moderation_enabled=True,
        )
        session.add(channel)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="add_channel",
            details=f"Channel: {channel_id}, Name: {name}",
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

    await message.answer(f"Канал {name} добавлен.")
    await state.clear()


# Хендлер для удаления канала
@router.callback_query(F.data == "remove_channel")
async def start_remove_channel(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await callback.message.answer("Нет активных каналов.")
        return

    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=channel.name, callback_data=f"remove_channel_{channel.id}")
    builder.adjust(1)

    await callback.message.answer(
        "Выберите канал для удаления:", reply_markup=builder.as_markup()
    )
    await callback.answer()


# Хендлер для подтверждения удаления канала
@router.callback_query(F.data.startswith("remove_channel_"))
async def confirm_remove_channel(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    channel_id = int(callback.data.split("_")[2])
    async with db_session as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            await callback.message.answer("Канал не найден.")
            return

        channel.is_active = False
        session.add(channel)

        # Логируем действие
        log = Log(
            user_id=callback.from_user.id,
            action="remove_channel",
            details=f"Channel: {channel_id}",
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

    await callback.message.answer(f"Канал {channel.name} удален.")
    await callback.answer()


# Хендлер для списка каналов
@router.callback_query(F.data == "list_channels")
async def list_channels(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await callback.message.answer("Нет активных каналов.")
        return

    text = "Список каналов:\n" + "\n".join(
        [f"ID: {ch.id}, Name: {ch.name}" for ch in channels]
    )
    await callback.message.answer(text)
    await callback.answer()


# Хендлер для просмотра статистики
@router.callback_query(F.data == "view_stats")
async def view_stats(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Показать статистику", callback_data="show_stats")
    builder.button(text="Экспортировать в CSV", callback_data="export_stats")
    builder.adjust(1)

    await callback.message.answer("Статистика:", reply_markup=builder.as_markup())
    await callback.answer()


# Хендлер для показа статистики
@router.callback_query(F.data == "show_stats")
async def show_stats(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(
            select(Stat).join(Channel).filter(Channel.is_active == True)
        )
        stats = result.scalars().all()

    if not stats:
        await callback.message.answer("Нет данных для статистики.")
        return

    text = "Статистика по каналам:\n"
    for stat in stats:
        channel = await session.get(Channel, stat.channel_id)
        text += f"Канал: {channel.name}, Пост ID: {stat.post_id or 'N/A'}, Просмотры: {stat.views}, Комментарии: {stat.comments}\n"

    await callback.message.answer(text)
    await callback.answer()


# Хендлер для экспорта статистики в CSV
@router.callback_query(F.data == "export_stats")
async def export_stats(
    callback: types.CallbackQuery, db_manager: DatabaseManager, bot: Bot
):
    db_session = db_manager.get_async_session()
    if not await is_admin(callback.from_user.id, db_session):
        await callback.message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(
            select(Stat).join(Channel).filter(Channel.is_active is True)
        )
        stats = result.scalars().all()

    if not stats:
        await callback.message.answer("Нет данных для экспорта.")
        return

    # Формируем DataFrame
    data = [
        {
            "channel_id": stat.channel_id,
            "post_id": stat.post_id,
            "views": stat.views,
            "comments": stat.comments,
            "timestamp": stat.timestamp,
        }
        for stat in stats
    ]
    df = pd.DataFrame(data)

    # Сохраняем в CSV
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_file = types.BufferedInputFile(
        csv_buffer.getvalue().encode(), filename="stats.csv"
    )

    await bot.send_document(callback.message.chat.id, csv_file)
    await callback.answer()


# Хендлер для просмотра логов
@router.message(Command("logs"))
async def cmd_logs(message: types.Message, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin(message.from_user.id, db_session):
        await message.answer("Доступ только для администраторов.")
        return

    async with db_session as session:
        result = await session.execute(
            select(Log).order_by(Log.timestamp.desc()).limit(50)
        )
        logs = result.scalars().all()

    if not logs:
        await message.answer("Нет логов.")
        return

    text = "Последние логи:\n"
    for log in logs:
        user = await session.get(User, log.user_id)
        text += f"[{log.timestamp.strftime('%Y-%m-%d %H:%M')}] {log.action} by @{user.username or log.user_id}: {log.details}\n"

    await message.answer(text)
