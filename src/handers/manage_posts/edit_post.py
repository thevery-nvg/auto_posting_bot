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
from src.handers.mock import channels as mock_channels
from src.handers.mock import Post, PostStatus, posts_mock, posts_mock_dict
from src.handers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    get_post_details,
    get_post_details_keyboard,
)

router = Router(name="edit_post")


@router.callback_query(F.data.startswith("post_"), Admin.manage_posts)
async def view_post(callback_query: types.CallbackQuery, state: FSMContext):
    post_id = int(callback_query.data.replace("post_", ""))
    await state.update_data(post_id=post_id)
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = None
    for p in posts:
        if p.id == post_id:
            post = p
            break
    await state.update_data(post=post)
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_title_callback, Admin.manage_posts)
async def edit_post_title_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_title)
    await main_message.message.edit_text(
        "Введите новый текст заголовка поста:",
    )


@router.message(Admin.edit_post_title)
async def edit_post_title_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    text = message.text
    await message.delete()
    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].title = text
            post.title = text
            break
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_callback, Admin.manage_posts)
async def edit_post_text_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_text)
    await main_message.message.edit_text(
        "Введите новый текст поста:",
    )


@router.message(Admin.edit_post_text)
async def edit_post_text_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    text = message.text
    await message.delete()
    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].text = text
            post.text = text
            break
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )
