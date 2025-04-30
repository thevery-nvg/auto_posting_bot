from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.core.models import Channel, Post, PostStatus, UserRole, User
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import pendulum
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.database import DatabaseManager

router = Router()


# Определяем FSM для создания поста
class CreatePost(StatesGroup):
    select_channel = State()
    enter_text = State()
    add_media = State()
    set_time = State()


# Функция для проверки прав админа или модератора
async def is_admin_or_moderator(user_id: int, db_session: AsyncSession) -> bool:
    async with db_session as session:
        user = await session.get(User, user_id)
        return user and user.role in [UserRole.ADMIN, UserRole.MODERATOR]


# Инициализация планировщика
scheduler = AsyncIOScheduler()


# Функция для публикации поста
async def publish_post(bot: Bot, post_id: int, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    async with db_session as session:
        post = await session.get(Post, post_id)
        if not post or post.status != PostStatus.PENDING:
            return

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
                    chat_id=post.channel_id, text=post.text, parse_mode="Markdown"
                )

            # Обновляем статус поста
            post.status = PostStatus.PUBLISHED
            await session.commit()
        except Exception as e:
            # Логируем ошибку (можно добавить в таблицу logs)
            print(f"Error publishing post {post_id}: {e}")
            post.status = PostStatus.CANCELLED
            await session.commit()


# Хендлер для команды /create_post
@router.message(Command("create_post"))
async def cmd_create_post(
    message: types.Message, state: FSMContext, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer("Только админы и модераторы могут создавать посты.")
        return

    # Получаем список активных каналов
    async with db_session as session:
        result = await session.execute(select(Channel).filter_by(is_active=True))
        channels = result.scalars().all()

    if not channels:
        await message.answer("Нет активных каналов для публикации.")
        return

    # Создаем клавиатуру с каналами
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.button(text=channel.name, callback_data=f"channel_{channel.id}")
    builder.adjust(1)

    await message.answer(
        "Выберите канал для публикации:", reply_markup=builder.as_markup()
    )
    await state.set_state(CreatePost.select_channel)


# Хендлер для выбора канала
@router.callback_query(F.data.startswith("channel_"), CreatePost.select_channel)
async def select_channel(
    callback: types.CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    channel_id = int(callback.data.split("_")[1])
    async with db_session as session:
        channel = await session.get(Channel, channel_id)
        if not channel:
            await callback.message.answer("Канал не найден.")
            await state.clear()
            return

    await state.update_data(channel_id=channel_id)
    await callback.message.answer(
        "Введите текст поста (или отправьте '-' для поста без текста):"
    )
    await state.set_state(CreatePost.enter_text)
    await callback.answer()


# Хендлер для ввода текста
@router.message(CreatePost.enter_text)
async def enter_text(message: types.Message, state: FSMContext):
    text = message.text if message.text != "-" else None
    await state.update_data(text=text)
    await message.answer(
        "Отправьте медиа (фото, видео, документ) или нажмите кнопку 'Пропустить'.",
        reply_markup=InlineKeyboardBuilder()
        .button(text="Пропустить", callback_data="skip_media")
        .as_markup(),
    )
    await state.set_state(CreatePost.add_media)


# Хендлер для пропуска медиа
@router.callback_query(F.data == "skip_media", CreatePost.add_media)
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(media_type=None, media_file_id=None)
    await callback.message.answer(
        "Введите время публикации (например, 2025-04-30 14:00):"
    )
    await state.set_state(CreatePost.set_time)
    await callback.answer()


# Хендлер для добавления медиа
@router.message(
    CreatePost.add_media, F.content_type.in_({"photo", "video", "document"})
)
async def add_media(message: types.Message, state: FSMContext):
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
    await message.answer("Введите время публикации (например, 2025-04-30 14:00):")
    await state.set_state(CreatePost.set_time)


# Хендлер для установки времени
@router.message(CreatePost.set_time)
async def set_time(
    message: types.Message, state: FSMContext, db_manager: DatabaseManager, bot: Bot):
    db_session = db_manager.get_async_session()
    try:
        publish_time = pendulum.parse(message.text, strict=False).replace(tzinfo=None)
        if publish_time < datetime.now():
            await message.answer("Время публикации должно быть в будущем.")
            return
    except ValueError:
        await message.answer(
            "Неверный формат времени. Используйте, например, 2025-04-30 14:00."
        )
        return

    # Получаем данные из FSM
    data = await state.get_data()
    channel_id = data["channel_id"]
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

    await message.answer(
        f"Пост запланирован на {publish_time.strftime('%Y-%m-%d %H:%M')}."
    )
    await state.clear()


# Хендлер для списка запланированных постов
@router.message(Command("list_scheduled"))
async def list_scheduled(message: types.Message, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    if not await is_admin_or_moderator(message.from_user.id, db_session):
        await message.answer(
            "Только админы и модераторы могут просматривать запланированные посты."
        )
        return

    async with db_session as session:
        result = await session.execute(
            select(Post)
            .filter_by(status=PostStatus.PENDING)
            .order_by(Post.publish_time)
        )
        posts = result.scalars().all()

    if not posts:
        await message.answer("Нет запланированных постов.")
        return

    builder = InlineKeyboardBuilder()
    for post in posts:
        channel = await session.get(Channel, post.channel_id)
        text = f"Канал: {channel.name}, Время: {post.publish_time.strftime('%Y-%m-%d %H:%M')}"
        builder.button(text=text, callback_data=f"view_post_{post.id}")
    builder.adjust(1)

    await message.answer("Запланированные посты:", reply_markup=builder.as_markup())


# Хендлер для просмотра поста
@router.callback_query(F.data.startswith("view_post_"))
async def view_post(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    post_id = int(callback.data.split("_")[2])
    async with db_session as session:
        post = await session.get(Post, post_id)
        if not post:
            await callback.message.answer("Пост не найден.")
            return

        channel = await session.get(Channel, post.channel_id)
        text = (
            f"Канал: {channel.name}\n"
            f"Текст: {post.text or 'Нет текста'}\n"
            f"Медиа: {post.media_type or 'Нет медиа'}\n"
            f"Время: {post.publish_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Статус: {post.status.value}"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="Редактировать", callback_data=f"edit_post_{post.id}")
        builder.button(text="Удалить", callback_data=f"delete_post_{post.id}")
        builder.adjust(2)

        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# Хендлер для удаления поста
@router.callback_query(F.data.startswith("delete_post_"))
async def delete_post(callback: types.CallbackQuery, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    post_id = int(callback.data.split("_")[2])
    async with db_session as session:
        post = await session.get(Post, post_id)
        if not post:
            await callback.message.answer("Пост не найден.")
            return

        post.status = PostStatus.CANCELLED
        await session.commit()

        # Удаляем задачу из планировщика
        scheduler.remove_job(f"post_{post_id}")

        await callback.message.answer("Пост отменен.")
    await callback.answer()


# Хендлер для редактирования поста (заглушка, можно расширить)
@router.callback_query(F.data.startswith("edit_post_"))
async def edit_post(
    callback: types.CallbackQuery, state: FSMContext, db_manager: DatabaseManager):
    db_session = db_manager.get_async_session()
    post_id = int(callback.data.split("_")[2])
    async with db_session as session:
        post = await session.get(Post, post_id)
        if not post:
            await callback.message.answer("Пост не найден.")
            return

        # Сохраняем ID поста для редактирования
        await state.update_data(post_id=post_id, channel_id=post.channel_id)
        await callback.message.answer(
            "Введите новый текст поста (или отправьте '-' для поста без текста):"
        )
        await state.set_state(CreatePost.enter_text)
    await callback.answer()


# Запуск планировщика при старте бота
@router.startup()
async def on_startup():
    scheduler.start()


# Остановка планировщика при завершении
@router.shutdown()
async def on_shutdown():
    scheduler.shutdown()
