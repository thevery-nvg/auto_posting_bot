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
from src.handers.mock import Post,PostStatus,publish_post
from src.handers.utils import (
    is_user_admin,
    log_action,
    check_admin_access,
    Buttons,
    goto_main_menu_btn,
Admin
)

router = Router(name="manage_posts")
scheduler = AsyncIOScheduler()

@router.callback_query(F.data == Buttons.manage_posts_callback, Admin.main)
async def manage_posts(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.create_post_text, callback_data=Buttons.create_post_callback)
    builder.button(text=Buttons.remove_post_text, callback_data=Buttons.remove_post_callback)
    builder.button(text=Buttons.list_posts_text, callback_data=Buttons.list_posts_callback)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(text="📢 Выберите действие:", reply_markup=builder.as_markup())


@router.callback_query(F.data == Buttons.create_post_callback, Admin.manage_posts)
async def create_post(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channels = mock_channels
    main_message = data.get("main_message")
    if not channels:
        await main_message.message.edit_text(text="❌ Каналы не найдены.",
                                             reply_markup=InlineKeyboardBuilder().button(**goto_main_menu_btn).as_markup())
        return

    # Создаем клавиатуру с каналами
    page_size = 5
    page = data.get("page", 0)
    total_pages = len(channels) // page_size
    message_text = f"📢 Выберите канал для публикации: ({total_pages}):\n\n"
    builder = InlineKeyboardBuilder()
    for channel in channels[page : page + page_size]:
        builder.button(
            text=f"{channel.name} [{channel.id}]",
            callback_data=f"channel_{channel.id}",
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
    main_message = callback_query
    await state.update_data(main_message=main_message)
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
async def enter_text(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    channel = None
    for c in channels:
        if c.id == channel_id:
            channel = c
            break
    await main_message.message.edit_text(
        text=f"📢 Введите текст для публикации в канал {channel.name} [{channel.id}]:",
    )
    await state.set_state(Admin.manage_posts_enter_text)
    await state.update_data(channel_id=channel_id)


@router.message(Admin.manage_posts_enter_text)
async def process_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    text = message.text
    await message.delete()
    await state.update_data(text=text)
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.skip_media_text, callback_data=Buttons.skip_media_callback)
    builder.adjust(1)
    await state.set_state(Admin.manage_posts_media)
    await main_message.message.edit_text(
        "Отправьте медиа (фото, видео, документ) или нажмите кнопку 'Пропустить'.",
        reply_markup=builder.as_markup(),
    )

# Хендлер для пропуска медиа
@router.callback_query(F.data == Buttons.skip_media_callback,Admin.manage_posts_media)
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.update_data(media_type=None, media_file_id=None)
    await state.set_state(Admin.manage_posts_set_time)
    await main_message.message.edit_text(
        "Введите время публикации (например, 2025-04-30 14:00):"
    )


# Хендлер для добавления медиа
@router.message(F.content_type.in_({"photo", "video", "document"}),Admin.manage_posts_media)
async def add_media(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
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
    await state.update_data(media_type=media_type, media_file_id=media_file_id)
    await message.delete()
    await state.set_state(Admin.manage_posts_set_time)
    await main_message.message.edit_text(
        "Введите время публикации (например, 2025-04-30 14:00):"
    )


# Хендлер для установки времени
@router.message(Admin.manage_posts_set_time)
async def set_time(
    message: types.Message, state: FSMContext, db_session:AsyncSession, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        publish_time = pendulum.parse(message.text, strict=False).replace(tzinfo=None)
        if publish_time < datetime.now():
            await main_message.message.edit_text("Время публикации должно быть в будущем.")
            return
    except ValueError:
        await main_message.message.edit_text( "Неверный формат времени. Используйте, например, 2025-04-30 14:00.")
        return

    # Получаем данные из FSM
    data = await state.get_data()
    channel_id = data.get("channel_id")
    text = data.get("text")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")

    # Сохраняем пост в базу
    async with db_session as session:
        post = Post(
            channel_id=channel_id,
            text=text,
            media_type=media_type,
            media_file_id=media_file_id,
            publish_time=publish_time,
            created_by=message.from_user.id,
            status=PostStatus.PENDING,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)

        # Добавляем задачу в планировщик
        scheduler.add_job(
            publish_post,
            trigger=DateTrigger(run_date=publish_time),
            args=[bot, post.id, db_session],
            id=f"post_{post.id}",
        )
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(text=f"Пост запланирован на {publish_time.strftime('%Y-%m-%d %H:%M')}.",
                                         reply_markup=builder.as_markup())


# Запуск планировщика при старте бота
@router.startup()
async def on_startup():
    scheduler.start()


# Остановка планировщика при завершении
@router.shutdown()
async def on_shutdown():
    scheduler.shutdown()
