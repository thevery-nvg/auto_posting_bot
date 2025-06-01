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
    publish_post,
)

router = Router(name="edit_post")


@router.callback_query(F.data.startswith("post_"), Admin.posts_list)
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
    await state.set_state(Admin.manage_posts_details)
    await state.update_data(post=post)
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_title_callback, Admin.manage_posts_details)
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
    await state.set_state(Admin.posts_list)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_callback, Admin.posts_list)
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
    await state.set_state(Admin.posts_list)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data == Buttons.edit_time_callback, Admin.posts_list)
async def edit_post_time_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_time)
    await main_message.message.edit_text(
        "Введите новое время публикации (например, 2025-04-30 14:00):"
    )


@router.message(Admin.edit_post_time)
async def edit_post_time_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    try:
        publish_time = pendulum.parse(message.text, strict=False).replace(tzinfo=None)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Неверный формат времени. Используйте, например, 2025-04-30 14:00."
        )
        return
    if publish_time < datetime.now():
        await main_message.message.edit_text(
            "❌Время публикации должно быть в будущем."
        )
        return
    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].publish_time = publish_time
            post.publish_time = publish_time
            break
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.update_data(posts=posts)
    await state.set_state(Admin.posts_list)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_remove_media_callback, Admin.posts_list)
async def edit_remove_media(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].media_file_id = None
            posts[i].media_type = None
            break
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.update_data(posts=posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_add_media_callback, Admin.posts_list)
async def edit_add_media_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_media)
    await main_message.message.edit_text("Отправьте медиа (фото, видео, документ):")


@router.message(Admin.edit_post_media, F.photo | F.video | F.document)
async def edit_add_media_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    media_type = None
    media_file_id = None

    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        media_file_id = message.video.file_id
    elif message.document:
        media_type = "document"
        media_file_id = message.document.file_id

    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].media_file_id = media_file_id
            posts[i].media_type = media_type
            post.media_file_id = media_file_id
            post.media_type = media_type
            break
    await state.update_data(posts=posts)
    await message.delete()
    await state.set_state(Admin.posts_list)
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data == Buttons.cancel_post_callback, Admin.posts_list)
async def cancel_post(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    for i, p in enumerate(posts):
        if p.id == post.id:
            posts[i].status=PostStatus.CANCELLED
            post.status=PostStatus.CANCELLED
            break
    await state.update_data(posts=posts,post=post)
    details = get_post_details(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data == Buttons.publish_now_callback, Admin.posts_list)
async def publish_now_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    builder=InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Да", callback_data=Buttons.yes_sure_callback),
        InlineKeyboardButton(text="Нет", callback_data=Buttons.no_god_no_callback),
    )
    await main_message.message.edit_text("Вы уверены, что хотите опубликовать пост сейчас?",
                                         reply_markup=builder.as_markup())

@router.callback_query(F.data.contains(Buttons.yes_sure_callback)
                       |F.data.contains(Buttons.no_god_no_callback),
                       Admin.posts_list)
async def publish_now_stage_2(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    post = data.get("post")
    builder=InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    if callback_query.data==Buttons.yes_sure_callback:
        await publish_post(bot, post)
        await main_message.message.edit_text(
            "Пост опубликован!", reply_markup=builder.as_markup()
        )
    else:
        details = get_post_details(post)
        builder = get_post_details_keyboard(post)
        await main_message.message.edit_text(
            text=details,
            reply_markup=builder.as_markup(),
        )
