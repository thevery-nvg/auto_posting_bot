from datetime import datetime
import pendulum
from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import get_active_channels, add_post, get_channel_by_id
from src.handlers.manage_posts.shedule import scheduler
from src.handlers.mock import Post, PostStatus
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    publish_post,
    go_to_main_menu_keyboard,
)

router = Router(name="create_post")


@router.callback_query(
    F.data == Buttons.create_post_callback,
    Admin.manage_posts,
)
async def create_post_stage_1(callback: CallbackQuery,state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    # Получаем каналы
    channels = await get_active_channels(db_session)

    main_message = data.get("main_message")
    if not channels:
        await main_message.message.edit_text(
            text="❌ Каналы не найдены.",
            reply_markup=go_to_main_menu_keyboard()
        )
        return
    # Создаем клавиатуру с каналами`
    page_size = 5
    page = 0
    total_pages = len(channels) // page_size
    message_text = f"📢 Выберите канал для публикации: ({total_pages}):\n\n"
    builder = InlineKeyboardBuilder()
    for channel in channels[page : page + page_size]:
        callback_data = f"channel_{channel.id}"
        builder.button(
            text=f"{channel.name} {channel.id}",
            callback_data=callback_data,
        )
    data["page"] = page + page_size
    data["channels"] = channels
    await state.set_data(data)
    if page + page_size < len(channels):
        builder.button(
            text=Buttons.forward_text, callback_data=Buttons.forward_callback
        )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(
    F.data.contains(Buttons.back_callback) | F.data.contains(Buttons.forward_callback),
    Admin.manage_posts,
)
async def change_page(callback_query: types.CallbackQuery, state: FSMContext):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels")
    page = data.get("page")
    total_pages = len(channels) // page_size
    if callback_query.data == Buttons.back_callback:
        page -= page_size
    if callback_query.data == Buttons.forward_callback:
        page += page_size
    await state.update_data(page=page)
    builder = InlineKeyboardBuilder()

    for channel in channels[page : page + page_size]:
        callback_data = f"channel_{channel.id}"
        builder.button(
            text=f"{channel.name} {channel.id}",
            callback_data=callback_data,
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
        if page + page_size < len(channels)
        else None
    )
    navigation = [back, forward]

    builder.row(*[x for x in navigation if x])
    builder.button(**goto_main_menu_btn)
    message_text = f"📢 Выберите канал для публикации: ({total_pages}):\n\n"

    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("channel_"), Admin.manage_posts)
async def create_post_stage_2(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    channel_id = int(callback_query.data.replace("channel_", ""))
    channel = await get_channel_by_id(db_session, channel_id)
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.update_data(channel=channel)
    await state.set_state(Admin.manage_posts_set_title)
    await main_message.message.edit_text(
        text=f"📢 Введите заголовок для публикации в канал {channel.name} [{channel.id}]:",
    )


@router.message(Admin.manage_posts_set_title)
async def create_post_stage_3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    title = message.text
    await message.delete()
    await state.update_data(title=title)
    await state.set_state(Admin.manage_posts_enter_text)
    await main_message.message.edit_text(
        text=f"📢 Введите текст для публикации:",
    )


@router.message(Admin.manage_posts_enter_text)
async def process_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    text = message.text
    await message.delete()
    await state.update_data(text=text)
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.skip_media_text, callback_data=Buttons.skip_media_callback
    )
    builder.adjust(1)
    await state.set_state(Admin.manage_posts_media)
    await main_message.message.edit_text(
        "Отправьте медиа (фото, видео, документ) или нажмите кнопку 'Пропустить'.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.skip_media_callback, Admin.manage_posts_media)
#пропуск медиа или завершение медиа
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.manage_posts_set_time)
    await main_message.message.edit_text(
        "Введите время публикации (например, 2025-04-30 14:00):"
    )


@router.message(F.content_type.in_({"photo", "video", "document"}), Admin.manage_posts_media)
async def add_media(message: types.Message, state: FSMContext,bot:Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    photos = data.get("photos", list())
    videos = data.get("videos", list())
    docs = data.get("docs", None)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Далее", callback_data=Buttons.skip_media_callback
    )
    builder.adjust(1)
    if message.photo:
        photos.append(message.photo[-1].file_id)
    if message.video:
        videos.append(message.video.file_id)
    if message.document:
        if not docs:
            docs = message.document.file_id
        else:
            await main_message.message.edit_text(
                chat_id=message.chat.id,
                text="Можно прикрепить только один документ.\n\nОтправьте фото или видео или нажмите кнопку 'Далее'.",
                reply_markup=builder.as_markup(),
            )
            return
    await state.update_data(photos=photos, videos=videos, docs=docs)
    await main_message.message.edit_text(chat_id=message.chat.id,
                           text= "Отправьте медиа (фото, видео или документ) или нажмите кнопку 'Далее'.",
                           reply_markup=builder.as_markup())



# Хендлер для установки времени
@router.message(Admin.manage_posts_set_time)
async def set_time(
    message: types.Message, state: FSMContext, db_session: AsyncSession, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        publish_time = pendulum.parse(message.text, strict=False).replace(tzinfo=None)
        await message.delete()
        if publish_time < datetime.now():
            await main_message.message.edit_text(
                "❌Время публикации должно быть в будущем."
            )

            return
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Неверный формат времени. Используйте, например, 2025-04-30 14:00."
        )
        return

    # Получаем данные из FSM
    channel = data.get("channel")
    text = data.get("text")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    title = data.get("title")

    # Сохраняем пост в базу
    post = Post(
        title=title,
        channel_id=channel.id,
        text=text,
        media_type=media_type,
        media_file_id=media_file_id,
        publish_time=publish_time,
        created_by=message.from_user.id,
        status=PostStatus.PENDING,
    )
    post = await add_post(db_session, post)

    scheduler.add_job(
        publish_post,
        trigger=DateTrigger(run_date=publish_time),
        args=[post.id],
        id=f"post_{post.id}",
        replace_existing=True,
    )
    await main_message.message.edit_text(
        text=f"Пост запланирован на {publish_time.strftime('%Y-%m-%d %H:%M')}.",
        reply_markup=go_to_main_menu_keyboard(),
    )
