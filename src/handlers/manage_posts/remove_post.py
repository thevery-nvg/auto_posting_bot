from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound, MultipleResultsFound, SQLAlchemyError
# from src.core.models import Channel, Post, PostStatus, UserRole, User
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import pendulum
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
)
from src.core.crud import delete_post,get_post_by_id

router = Router(name="remove_post")

@router.callback_query(F.data == Buttons.remove_post_callback, Admin.manage_posts)
async def remove_post_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_post)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text="Введите ID поста для удаления:",
        reply_markup=builder.as_markup(),
    )
@router.message(Admin.remove_post)
async def remove_post_stage_2(message: types.Message, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    try:
        post_id =int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            text="❌ Неверный формат ID поста. Введите число.",
            reply_markup=builder.as_markup(),
        )
        return
    try:
        post=await get_post_by_id(db_session,post_id)

    except NoResultFound:
        await main_message.message.edit_text(
            text="❌ Пост не найден.Введите корректный ID поста.",
            reply_markup=builder.as_markup(),
        )
        return
    except MultipleResultsFound:
        await main_message.message.edit_text(
            text="❌ Найдено несколько постов с таким ID. Обратитесь к администратору.",
            reply_markup=builder.as_markup(),
        )
        return
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching post {post_id}: {e}")
        await main_message.message.edit_text(
            text="❌ Ошибка базы данных. Попробуйте позже.",
            reply_markup=builder.as_markup(),
        )
        return
    await delete_post(db_session,post)
    await main_message.message.edit_text(
        text=f"✅ Пост [{post_id}] удален.",
        reply_markup=builder.as_markup(),
    )
