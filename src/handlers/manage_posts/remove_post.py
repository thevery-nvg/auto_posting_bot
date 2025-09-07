from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# from src.core.models import Channel, Post, PostStatus, UserRole, User
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import pendulum
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.handlers.mock import channels as mock_channels
from src.handlers.mock import Post, PostStatus,posts_mock,posts_mock_dict
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
)

router = Router(name="remove_post")

@router.callback_query(F.data == Buttons.remove_post_callback, Admin.manage_posts)
async def remove_post_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(posts=posts_mock)
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_post)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text="Введите ID поста для удаления:",
        reply_markup=builder.as_markup(),
    )
@router.message(Admin.remove_post)
async def remove_post_stage_2(message: types.Message, state: FSMContext):
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
    posts=data.get("posts")
    for post in posts:
        if post.id == post_id:
            posts.remove(post)
            break
    else:
        await main_message.message.edit_text(
            text="❌ Пост не найден.Введите корректный ID поста.",
            reply_markup=builder.as_markup(),
        )
        return
    await state.update_data(posts=posts)
    await main_message.message.edit_text(
        text=f"✅ Пост [{post_id}] удален.",
        reply_markup=builder.as_markup(),
    )
