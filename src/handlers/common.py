import random
from datetime import datetime, timedelta

from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from handlers.utils import Buttons
from src.core.models import User, UserRole, PostStatus, Post, Channel

router = Router(name="common")
example_router = Router(name="example")


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_session: AsyncSession):
    logger.info(f"Received /start command from [{message.from_user.id}]")
    user = await db_session.get(User, message.from_user.id)
    if not user:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            role=UserRole.USER,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.close()
    await message.answer(f"Welcome, {user.id=} {user.username=}!")



@router.message(Command("write"))
async def cmd_write(message: types.Message, db_session: AsyncSession):
    logger.info(f"Received /write command from [{message.from_user.id}]")
    channel = Channel(
        comment_chat_id=-1002657911055,
        name="ARCANE",
        id=-1002164486161,
        notification_chat_id=0,
    )
    await add_channel(db_session, channel)
    for i in range(20):
        channel = Channel(
            comment_chat_id=-1002657911055+i,
            name=f"Test channel {i}",
            id=-1002164486161 + i,
            notification_chat_id=0,
        )
        await add_channel(db_session, channel)
    logger.info(f"channels have been written to db")
    for i in range(20):
        post = Post(
            created_by=5528297066,
            channel_id=-1002164486161,
            title=f"Test title {i}",
            text=f"Test text {i}",
            publish_time=datetime.now() + timedelta(seconds=random.randint(600, 1800)),
        )
        await add_post(db_session, post)
    logger.info(f"posts have been written to db")


from src.core.crud import (
    get_pending_posts,
    update_post,
    add_channel,
    add_post,
)


@router.message(Command("change_status"))
async def change_status(message: types.Message, db_session: AsyncSession):
    logger.info(f"Received /change_status command from [{message.from_user.id}]")
    posts = await get_pending_posts(db_session)
    for post in posts:
        logger.info(f"post status={post.status}")
        post.status = PostStatus.PUBLISHED
        logger.info(f"post status changed ={post.status}")
        await update_post(db_session, post)


# Пример хендлера с явным управлением сессией
@example_router.message(F.text == "/profile")
async def show_profile(
    message: types.Message, session_factory: async_sessionmaker[AsyncSession]
):
    async with session_factory() as session:
        # Явное создание и управление сессией
        try:
            user = await session.get(User, message.from_user.id)

            if not user:
                await message.answer("Вы не зарегистрированы в системе!")
                return

            await message.answer(
                f"📌 Ваш профиль:\n\n"
                f"🆔 ID: {user.id}\n"
                f"👤 Имя: {user.full_name}\n"
                f"🔗 Username: @{user.username or 'не указан'}\n"
                f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
            )

        except Exception as e:
            await session.rollback()
            await message.answer("⚠️ Произошла ошибка при получении профиля")
            logger.error(f"Database error: {e}")
            raise

        finally:
            await session.close()


# Пример хендлера с транзакцией
@example_router.message(F.text.startswith("/update_name "))
async def update_name(
    message: types.Message, session_factory: async_sessionmaker[AsyncSession]
):
    new_name = message.text.split(maxsplit=1)[1].strip()
    if not new_name:
        return await message.answer("❌ Укажите новое имя!")

    async with session_factory() as session:
        try:
            # Начинаем явную транзакцию
            async with session.begin():
                user = await session.get(User, message.from_user.id)

                if not user:
                    user = User(
                        id=message.from_user.id,
                        full_name=new_name,
                        username=message.from_user.username,
                    )
                    session.add(user)
                    await message.answer(f"✅ Вы зарегистрированы с именем: {new_name}")
                    return None
                else:
                    old_name = user.full_name
                    user.full_name = new_name
                    await message.answer(
                        f"✅ Имя успешно изменено:\n" f"С «{old_name}» на «{new_name}»"
                    )
                    return None

        except Exception as e:
            await message.answer("❌ Не удалось обновить имя")
            logger.error(f"Update name error: {e}")
            raise
