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
from src.handers.mock import Post, PostStatus,posts_mock,posts_mock_dict
from src.handers.utils import (
    is_user_admin,
    log_action,
    check_admin_access,
    Buttons,
    goto_main_menu_btn,
    Admin,
)

router = Router(name="manage_posts")
scheduler = AsyncIOScheduler()

def get_post_details(post):
    return (f"📢 Пост ID:{post.id}:\n\n"
            f"Заголовок: {post.title}\n\n"
            f"Текст:{post.text}\n\n"
            f"Медиа тип: {post.media_type}\n\n"
            f"Медиа файл: {post.media_file_id}\n\n"
            f"Создано пользователем: {post.created_by}\n\n"
            f"Статус: {post.status}\n\n"
            f"Время публикации: {post.publish_time.strftime('%Y-%m-%d %H:%M')}")

def get_post_details_keyboard(post):
    builder = InlineKeyboardBuilder()
    media_btn = (
        {"text": Buttons.edit_add_media_text, "callback_data": Buttons.edit_add_media_callback}
        if post.media_type is  None
        else {
            "text": Buttons.edit_remove_media_text,
            "callback_data": Buttons.edit_remove_media_callback,
        }
    )
    builder.button(text=Buttons.edit_title_text, callback_data=Buttons.edit_title_callback)
    builder.button(text=Buttons.edit_text, callback_data=Buttons.edit_callback)
    builder.button(
        text=Buttons.edit_time_text, callback_data=Buttons.edit_time_callback
    )
    builder.button(**media_btn)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder
# Функция для публикации поста
async def publish_post(bot: Bot, post: Post):
        try:
            if post.media_file_id and post.media_type:
                if post.media_type == "photo":
                    await bot.send_photo(
                        chat_id=post.channel_id,
                        photo=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
                elif post.media_type == "video":
                    await bot.send_video(
                        chat_id=post.channel_id,
                        video=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
                elif post.media_type == "document":
                    await bot.send_document(
                        chat_id=post.channel_id,
                        document=post.media_file_id,
                        caption=post.text,
                        parse_mode="Markdown",
                    )
            else:
                await bot.send_message(
                    chat_id=post.channel_id, text=post.text, parse_mode="Markdown")
        except Exception as e:
            print(e)


@router.callback_query(F.data == Buttons.manage_posts_callback, Admin.main)
async def manage_posts(callback_query: types.CallbackQuery, state: FSMContext):
    main_message = callback_query
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.create_post_text, callback_data=Buttons.create_post_callback
    )
    builder.button(
        text=Buttons.remove_post_text, callback_data=Buttons.remove_post_callback
    )
    builder.button(
        text=Buttons.list_posts_text, callback_data=Buttons.list_posts_callback
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await state.set_state(Admin.manage_posts)
    await state.update_data(main_message=main_message)
    await main_message.message.edit_text(
        text="📢 Выберите действие:", reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == Buttons.remove_post_callback, Admin.manage_posts)
async def remove_post_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_post)
    await main_message.message.edit_text(
        text="Введите ID поста для удаления:",
    )
@router.message(Admin.remove_post)
async def remove_post_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        post_id =int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            text="❌ Неверный формат ID поста. Введите число."
        )
        return
    posts=data.get("posts")
    for post in posts:
        if post.id == post_id:
            posts.remove(post)
            break
    else:
        await main_message.message.edit_text(
            text="❌ Пост не найден.Введите корректный ID поста."
        )
        return
    await state.update_data(posts=posts)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text=f"✅ Пост [{post_id}] удален.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.create_post_callback, Admin.manage_posts)
async def create_post_stage_1(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channels = mock_channels
    main_message = data.get("main_message")
    if not channels:
        await main_message.message.edit_text(
            text="❌ Каналы не найдены.",
            reply_markup=InlineKeyboardBuilder()
            .button(**goto_main_menu_btn)
            .as_markup(),
        )
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
async def create_post_stage_2(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    await state.update_data(channel_id=channel_id)
    channel = None
    for c in channels:
        if c.id == channel_id:
            channel = c
            break
    await state.update_data(channel=channel)
    await state.set_state(Admin.manage_posts_set_title)
    await main_message.message.edit_text(
        text=f"📢 Введите заголовок для публикации в канал {channel.name} [{channel.id}]:",
    )

@router.message(Admin.manage_posts_set_title)
async def create_post_stage_3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    text = message.text
    await message.delete()
    await state.update_data(title=text)
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


# Хендлер для пропуска медиа
@router.callback_query(F.data == Buttons.skip_media_callback, Admin.manage_posts_media)
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.update_data(media_type=None, media_file_id=None)
    await state.set_state(Admin.manage_posts_set_time)
    await main_message.message.edit_text(
        "Введите время публикации (например, 2025-04-30 14:00):"
    )


# Хендлер для добавления медиа
@router.message(
    F.content_type.in_({"photo", "video", "document"}), Admin.manage_posts_media
)
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
    message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts=data.get("posts")
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
    channel_id = data.get("channel_id")
    text = data.get("text")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    title=data.get("title")

    # Сохраняем пост в базу
    post = Post(
        title=title,
        channel_id=channel_id,
        text=text,
        media_type=media_type,
        media_file_id=media_file_id,
        publish_time=publish_time,
        created_by=message.from_user.id,
        status=PostStatus.PENDING,
    )
    posts.append(post)
    await state.update_data(posts=posts)
    scheduler.add_job(
        publish_post,
        trigger=DateTrigger(run_date=publish_time),
        args=[bot, post],
        id=f"post_{post.id}",
    )
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text=f"Пост запланирован на {publish_time.strftime('%Y-%m-%d %H:%M')}.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data==Buttons.list_posts_callback, Admin.manage_posts)
async def list_posts(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    import copy
    page_size = 10
    data = await state.get_data()
    main_message = data.get("main_message")
    posts=copy.copy(posts_mock)
    total_pages=len(posts)//page_size
    page=data.get("page",0)
    message_text=f"📢 Список постов:\n\n"
    builder=InlineKeyboardBuilder()
    for post in posts[page:page+page_size]:
        print(post.text)
        builder.button(text=f"{post.title}:{post.publish_time}",callback_data=f"post_{post.id}")
    data["page"]=page+page_size
    data["posts"]=posts
    await state.set_data(data)
    if page+page_size<len(posts):
        builder.button(text=Buttons.forward_text,callback_data=Buttons.forward_callback)
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
    page_size = 10
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    page = data.get("page")
    total_pages = len(posts) // page_size
    if callback_query.data == Buttons.back_callback:
        page -= page_size
    if callback_query.data == Buttons.forward_callback:
        page += page_size
    await state.update_data(page=page)
    builder = InlineKeyboardBuilder()

    for post in posts[page : page + page_size]:
        builder.button(
            text=f"{post.id}:{post.publish_time}", callback_data=f"post_{post.id}"
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
        if page + page_size < len(posts)
        else None
    )
    navigation = [back, forward]

    builder.row(*[x for x in navigation if x])
    builder.button(**goto_main_menu_btn)
    message_text = f"📢 Список постов:\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


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
    details=get_post_details(post)
    builder=get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_title_callback, Admin.manage_posts)
async def edit_post_title_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
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
    posts=data.get("posts")
    post=data.get("post")
    text=message.text
    await message.delete()
    for i,p in enumerate(posts):
        if p.id == post.id:
            posts[i].title=text
            post.title=text
            break
    details=get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_callback, Admin.manage_posts)
async def edit_post_text_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
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
    posts=data.get("posts")
    post=data.get("post")
    text=message.text
    await message.delete()
    for i,p in enumerate(posts):
        if p.id == post.id:
            posts[i].text=text
            post.text=text
            break
    details=get_post_details(post)
    builder = get_post_details_keyboard(post)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == Buttons.edit_time_callback, Admin.manage_posts)
async def edit_post_time_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
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
    posts=data.get("posts")
    post=data.get("post")
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
    for i,p in enumerate(posts):
        if p.id == post.id:
            posts[i].publish_time=publish_time
            post.publish_time=publish_time
            break
    details=get_post_details(post)
    builder=get_post_details_keyboard(post)
    await state.update_data(posts=posts)
    await state.set_state(Admin.manage_posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data==Buttons.edit_remove_media_callback,
                       Admin.manage_posts)
async def edit_remove_media(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts=data.get("posts")
    post=data.get("post")
    for i,p in enumerate(posts):
        if p.id == post.id:
            posts[i].media_file_id=None
            posts[i].media_type = None
            break
    details=get_post_details(post)
    builder=get_post_details_keyboard(post)
    await state.update_data(posts=posts)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )

@router.callback_query(F.data==Buttons.edit_add_media_callback,Admin.manage_posts)
async def edit_add_media_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.edit_post_media)
    await main_message.message.edit_text(
        "Отправьте медиа (фото, видео, документ):"
    )

@router.message(Admin.edit_post_media, F.photo | F.video | F.document)
async def edit_add_media_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    posts=data.get("posts")
    post=data.get("post")
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

    for i,p in enumerate(posts):
        if p.id == post.id:
            posts[i].media_file_id=media_file_id
            posts[i].media_type = media_type
            post.media_file_id=media_file_id
            post.media_type=media_type
            break
    await state.update_data(posts=posts)
    await message.delete()
    await state.set_state(Admin.manage_posts)
    details=get_post_details(post)
    builder=get_post_details_keyboard(post)
    await main_message.message.edit_text(
        text=details,
        reply_markup=builder.as_markup(),
    )


# Запуск планировщика при старте бота
@router.startup()
async def on_startup(bot: Bot):
    posts=posts_mock
    for post in posts:
        scheduler.add_job(
            publish_post,
            trigger=DateTrigger(run_date=post.publish_time),
            args=[bot, post],
            id=f"post_{post.id}",
        )
    scheduler.start()


# Остановка планировщика при завершении
@router.shutdown()
async def on_shutdown():
    scheduler.shutdown()

