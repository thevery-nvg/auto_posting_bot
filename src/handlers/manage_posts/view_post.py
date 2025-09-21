# from src.core.models import Channel, Post, PostStatus, UserRole, User
from datetime import datetime

import pendulum
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud import (
    get_post_by_id,
    update_post,
    get_active_channels,
    get_channel_by_id,
)
from core.models import PostStatus, Post
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    get_post_details_text,
    get_post_details_keyboard,
    publish_post,
    yes_no_keyboard,
)

router = Router(name="edit_post")


@router.callback_query(F.data.startswith("post_"), Admin.posts_list)
async def view_post(callback_query: types.CallbackQuery, state: FSMContext,db_session: AsyncSession):
    post_id = int(callback_query.data.replace("post_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    post=await get_post_by_id(db_session,post_id)
    await state.set_state(Admin.manage_posts_details)
    await state.update_data(post=post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(
    F.data == Buttons.edit_title_callback, Admin.manage_posts_details
)
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
async def edit_post_title_stage_2(message: types.Message, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    post = data.get("post")

    title = message.text
    await message.delete()

    post.title = title
    post=await update_post(db_session,post)
    await state.update_data(post=post)

    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.posts_list)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_callback, Admin.manage_posts_details)
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
async def edit_post_text_stage_2(message: types.Message, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    post = data.get("post")
    text = message.text
    await message.delete()

    post.text = text
    post=await update_post(db_session,post)
    await state.update_data(post=post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts_details)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_time_callback, Admin.manage_posts_details)
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
async def edit_post_time_stage_2(message: types.Message, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
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
    post.publish_time = publish_time
    post=await update_post(db_session,post)
    await state.update_data(post=post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts_details)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_remove_media_callback, Admin.manage_posts_details)
async def edit_remove_media(callback_query: types.CallbackQuery, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    post = data.get("post")
    post.media_file_id = None
    post.media_type = None
    post=await update_post(db_session,post)
    await state.update_data(post=post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.edit_post_media)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_add_media_callback, Admin.edit_post_media)
async def edit_add_media_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_media)
    await main_message.message.edit_text("Отправьте медиа (фото, видео, документ):")


@router.message(Admin.edit_post_media, F.photo | F.video | F.document)
async def edit_add_media_stage_2(message: types.Message, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
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

    post.media_file_id = media_file_id
    post.media_type = media_type
    post=await update_post(db_session,post)
    await state.update_data(post=post)
    await message.delete()
    await state.set_state(Admin.manage_posts_details)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.cancel_post_callback, Admin.manage_posts_details)
async def cancel_post(callback_query: types.CallbackQuery, state: FSMContext,db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    post = data.get("post")
    post.status = PostStatus.CANCELLED
    post=await update_post(db_session,post)
    await state.update_data(post=post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.publish_now_callback, Admin.manage_posts_details)
async def publish_now_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.publish_now)
    await main_message.message.edit_text(
        "Вы уверены, что хотите опубликовать пост сейчас?",
        reply_markup=yes_no_keyboard(),
    )


@router.callback_query(
    F.data.contains(Buttons.yes_sure_callback)
    | F.data.contains(Buttons.no_god_no_callback),
    Admin.publish_now,
)
async def publish_now_stage_2(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    post = data.get("post")
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    if callback_query.data == Buttons.yes_sure_callback:
        await publish_post(post.id)
        await state.set_state(Admin.manage_posts_details)
        await main_message.message.edit_text(
            "Пост опубликован!", reply_markup=builder.as_markup()
        )
    else:
        details = get_post_details_text(post)
        builder = get_post_details_keyboard(post)
        await state.set_state(Admin.manage_posts_details)
        await main_message.message.edit_text(
            text=details,
            reply_markup=builder.as_markup(),
        )


@router.callback_query(
    F.data.contains(Buttons.edit_channel_callback),
    Admin.manage_posts_details,
)

async def edit_post_channel_list(callback_query: types.CallbackQuery, state: FSMContext,db_session: AsyncSession):
    page_size = 5
    page = 0

    data = await state.get_data()
    main_message = data.get("main_message")
    channels = await get_active_channels(db_session)

    builder = InlineKeyboardBuilder()
    for channel in channels[:page_size]:
        builder.button(
            text=f"{channel.name} [{channel.id}]",
            callback_data=f"channel_{channel.id}",
        )

    await state.update_data(page=page, channels=channels)
    await state.set_state(Admin.edit_post_channel)
    if len(channels) > page_size:
        builder.button(
            text=Buttons.forward_text, callback_data=Buttons.forward_callback
        )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)

    message_text = f"📢 Выберите канал для публикации ({page=}):\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(
    F.data.contains(Buttons.back_callback) | F.data.contains(Buttons.forward_callback),
    Admin.edit_post_channel,
)
async def edit_post_channel_change_page(callback_query: types.CallbackQuery, state: FSMContext):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels")
    page = data.get("page")
    total_pages = len(channels) // page_size
    if callback_query.data == Buttons.back_callback:
        page -= 1
    if callback_query.data == Buttons.forward_callback:
        page += 1
    builder = InlineKeyboardBuilder()
    p = channels[page * page_size : page * page_size + page_size]
    n = channels[page * page_size : page * page_size + page_size + 1]
    for channel in p:
        builder.button(
            text=f"{channel.name} [{channel.id}]",
            callback_data=f"channel_{channel.id}",
        )
    builder.adjust(1)

    back = (
        InlineKeyboardButton(
            text=Buttons.back_text, callback_data=Buttons.back_callback
        )
        if page != 0
        else None
    )
    forward = (
        InlineKeyboardButton(
            text=Buttons.forward_text, callback_data=Buttons.forward_callback
        )
        if len(n) > len(p)
        else None
    )
    navigation = [back, forward]
    builder.row(*[x for x in navigation if x])
    builder.button(**goto_main_menu_btn)
    await state.update_data(page=page, channels=channels)

    message_text = f"📢 Выберите канал для публикации ({page=}):\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("channel_"), Admin.edit_post_channel)
async def edit_post_channel_chosen(callback_query: types.CallbackQuery, state: FSMContext,db_session: AsyncSession):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    post: Post =  data.get("post")
    post.channel_id=channel_id
    await state.update_data(post=post)
    post=await update_post(db_session,post)
    details = get_post_details_text(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts_details)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )

# async def send_media_with_captions(bot: Bot, chat_id: int):
#     media = [
#         InputMediaPhoto(
#             media="https://example.com/photo1.jpg",
#             caption="Первое фото",  # Подпись будет показана только у первого файла
#         ),
#         InputMediaPhoto(media="https://example.com/photo2.jpg"),
#         InputMediaVideo(
#             media="https://example.com/video1.mp4",
#             caption="Видео с котиком",  # Эта подпись не будет показана
#         ),
#     ]
#
#     await bot.send_media_group(chat_id=chat_id, media=media)
