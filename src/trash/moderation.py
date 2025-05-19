import re
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.core.models import Channel, Filter, User, UserRole, Log
from better_profanity import profanity
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import timedelta
from core.database import DatabaseManager

router = Router()


# Определяем FSM для настройки фильтров
class SetFilter(StatesGroup):
    select_channel = State()
    enter_keyword = State()
    enter_regex = State()

class UserAction(StatesGroup):
    ban = State()
    unban = State()



# Функция для проверки прав админа или модератора
async def is_admin_or_moderator(user_id: int, db_session:AsyncSession) -> bool:
    async with db_session as session:
        user = await session.get(User, user_id)
        return user and user.role in [UserRole.ADMIN, UserRole.MODERATOR]


# Функция для проверки комментария на фильтры
async def check_comment(
    text: str, channel_id: int, db_session:AsyncSession) -> tuple[bool, str]:
    async with db_session as session:
        result = await session.execute(
            select(Filter).filter_by(channel_id=channel_id, is_active=True)
        )
        filters = result.scalars().all()

        # Проверяем на мат
        if profanity.contains_profanity(text):
            return False, "Нецензурная лексика"

        # Проверяем ключевые слова и регулярные выражения
        for f in filters:
            if f.keyword and f.keyword.lower() in text.lower():
                return False, f"Ключевое слово: {f.keyword}"
            if f.regex and re.search(f.regex, text, re.IGNORECASE):
                return False, f"Регулярное выражение: {f.regex}"

        return True, ""


# Хендлер для обработки новых комментариев
@router.message(lambda message: message.chat.type in [ChatType.SUPERGROUP, ChatType.PRIVATE])
async def handle_comment(message: types.Message, db_session:AsyncSession, bot: Bot):
    # Проверяем, связан ли чат с каналом
    async with db_session as session:
        result = await session.execute(
            select(Channel).filter_by(notification_chat_id=message.chat.id)
        )
        channel = result.scalars().first()

        if not channel or not channel.moderation_enabled:
            return

        # Проверяем текст сообщения
        text = message.text or message.caption or ""
        is_valid, reason = await check_comment(text, channel.id, db_session)

        if not is_valid:
            # Удаляем сообщение
            try:
                await bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                print(f"Error deleting message: {e}")

            # Логируем нарушение
            log = Log(
                user_id=message.from_user.id,
                action="comment_deleted",
                details=f"Reason: {reason}",
                channel_id=channel.id,
                timestamp=datetime.now(),
            )
            session.add(log)
            await session.commit()

            # Отправляем уведомление админам
            if channel.notification_chat_id:
                await bot.send_message(
                    channel.notification_chat_id,
                    f"Комментарий от @{message.from_user.username or message.from_user.id} удален.\nПричина: {reason}",
                )


# Хендлер для команды /ban_user
@router.message(Command("ban_user"))
async def cmd_ban_user(
    message: types.Message, state: FSMContext, db_session:AsyncSession):
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer("Только админы и модераторы могут банить пользователей.")
        return

    await message.answer(
        "Введите ID пользователя и длительность бана в минутах (0 для постоянного бана):"
    )
    await state.set_state(UserAction.ban)


# Хендлер для ввода данных бана
@router.message(UserAction.ban)
async def process_ban_user(
    message: types.Message, state: FSMContext, db_session:AsyncSession, bot:Bot):
    try:
        user_id, duration = map(int, message.text.split())
    except ValueError:
        await message.answer(
            "Неверный формат. Укажите ID и длительность через пробел (например, '123456 60')."
        )
        return

    async with db_session as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            await state.clear()
            return

        # Находим чат, связанный с каналом
        result = await session.execute(
            select(Channel).filter_by(moderation_enabled=True)
        )

        channels = result.scalars().all()
        for channel in channels:
            if channel.notification_chat_id:
                try:
                    until_date = (
                        None
                        if duration == 0
                        else datetime.now() + timedelta(minutes=duration)
                    )
                    await bot.ban_chat_member(
                        chat_id=channel.notification_chat_id,
                        user_id=user_id,
                        until_date=until_date,
                    )
                except Exception as e:
                    print(f"Error banning user {user_id}: {e}")

        # Обновляем статус бана
        user.is_banned = True
        session.add(user)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="ban_user",
            details=f"User: {user_id}, Duration: {duration} minutes",
            channel_id=channel.id if channels else None,
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

        await message.answer(
            f"Пользователь {user_id} забанен на {duration or 'неограниченное'} минут."
        )
        await state.clear()


# Хендлер для команды /unban_user
@router.message(Command("unban_user"))
async def cmd_unban_user(
    message: types.Message, db_session:AsyncSession, bot: Bot):
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer(
            "Только админы и модераторы могут разбанивать пользователей."
        )
        return

    try:
        user_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer(
            "Укажите ID пользователя (например, '/unban_user 123456')."
        )
        return

    async with db_session as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("Пользователь не найден.")
            return

        # Находим чаты, связанные с каналами
        result = await session.execute(
            select(Channel).filter_by(moderation_enabled=True)
        )
        channels = result.scalars().all()
        for channel in channels:
            if channel.notification_chat_id:
                try:
                    await bot.unban_chat_member(
                        chat_id=channel.notification_chat_id, user_id=user_id
                    )
                except Exception as e:
                    print(f"Error unbanning user {user_id}: {e}")

        # Обновляем статус
        user.is_banned = False
        session.add(user)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="unban_user",
            details=f"User: {user_id}",
            channel_id=channel.id if channels else None,
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

        await message.answer(f"Пользователь {user_id} разбанен.")


# Хендлер для команды /set_filter
@router.message(Command("set_filter"))
async def cmd_set_filter(
    message: types.Message, state: FSMContext, db_session:AsyncSession):
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer("Только админы и модераторы могут настраивать фильтры.")
        return

    # Получаем список активных каналов
    async with db_session as session:
        result = await session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await message.answer("Нет активных каналов.")
        return

    # Создаем клавиатуру с каналами
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=channel.name, callback_data=f"filter_channel_{channel.id}")
    builder.adjust(1)

    await message.answer(
        "Выберите канал для настройки фильтра:", reply_markup=builder.as_markup()
    )
    await state.set_state(SetFilter.select_channel)


# Хендлер для выбора канала для фильтра
@router.callback_query(F.data.startswith("filter_channel_"), SetFilter.select_channel)
async def select_filter_channel(
    callback: types.CallbackQuery, state: FSMContext, db_session:AsyncSession):
    channel_id = int(callback.data.split("_")[2])
    async with db_session as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            await callback.message.answer("Канал не найден.")
            await state.clear()
            return

    await state.update_data(channel_id=channel_id)
    await callback.message.answer(
        "Введите ключевое слово для фильтра (или '-' для пропуска):"
    )
    await state.set_state(SetFilter.enter_keyword)
    await callback.answer()


# Хендлер для ввода ключевого слова
@router.message(SetFilter.enter_keyword)
async def enter_keyword(message: types.Message, state: FSMContext):
    keyword = message.text if message.text != "-" else None
    await state.update_data(keyword=keyword)
    await message.answer(
        "Введите регулярное выражение для фильтра (или '-' для пропуска):"
    )
    await state.set_state(SetFilter.enter_regex)


# Хендлер для ввода регулярного выражения
@router.message(SetFilter.enter_regex)
async def enter_regex(
    message: types.Message, state: FSMContext, db_session:AsyncSession):
    regex = message.text if message.text != "-" else None
    if regex:
        try:
            re.compile(regex)
        except re.error:
            await message.answer("Неверное регулярное выражение.")
            return

    data = await state.get_data()
    channel_id = data["channel_id"]
    keyword = data.get("keyword")

    async with db_session as session:
        filter_obj = Filter(
            channel_id=channel_id, keyword=keyword, regex=regex, is_active=True
        )
        session.add(filter_obj)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="set_filter",
            details=f"Channel: {channel_id}, Keyword: {keyword}, Regex: {regex}",
            channel_id=channel_id,
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

    await message.answer("Фильтр успешно добавлен.")
    await state.clear()


# Хендлер для команды /moderate
@router.message(Command("moderate"))
async def cmd_moderate(message: types.Message, db_session:AsyncSession):
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer("Только админы и модераторы могут управлять модерацией.")
        return

    try:
        channel_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("Укажите ID канала (например, '/moderate -100123456789').")
        return

    async with db_session as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            await message.answer("Канал не найден.")
            return

        channel.moderation_enabled = not channel.moderation_enabled
        session.add(channel)

        # Логируем действие
        log = Log(
            user_id=message.from_user.id,
            action="toggle_moderation",
            details=f"Channel: {channel_id}, Enabled: {channel.moderation_enabled}",
            channel_id=channel_id,
            timestamp=datetime.now(),
        )
        session.add(log)
        await session.commit()

        status = "включена" if channel.moderation_enabled else "выключена"
        await message.answer(f"Модерация для канала {channel.name} {status}.")
