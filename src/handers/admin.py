import pandas as pd
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func
from aiogram import Router, F, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, any_state
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from io import StringIO
from typing import Optional

from src.core.models import User, UserRole, Stat, Log
from src.handers.utils import is_user_admin, log_action, check_admin_access

router = Router(name="admin")

class Channel:
    def __init__(self, id_:int, name:str, is_active:bool, moderation_enabled:bool, notification_chat_id:int, created_at, updated_at):
        self.id = id_
        self.name = name
        self.is_active = is_active
        self.moderation_enabled = moderation_enabled
        self.notification_chat_id = notification_chat_id
        self.created_at = created_at
        self.updated_at = updated_at


class Admin(StatesGroup):
    main = State()
    list_channels = State()
    channel_details = State()
    change_channel_name = State()


class Buttons:
    # Main menu
    manage_channels_text = "Управление каналами"
    manage_channels_callback = "manage_channels"
    view_logs_text = "Просмотр логов"
    view_logs_callback = "view_logs"
    stats_text = "Статистика"
    stats_callback = "view_stats"
    # Manage channels
    add_channel_text = "Добавить канал"
    add_channel_callback = "add_channel"
    remove_channel_text = "Удалить канал"
    remove_channel_callback = "remove_channel"
    list_channels_text = "Список каналов"
    list_channels_callback = "list_channels"
    forward_text = "Вперед"
    forward_callback = "#forward#"
    back_text = "Назад"
    back_callback = "#back#"
    goto_main_text = "Главное меню"
    goto_main_callback = "#main_menu#"


goto_main_menu_btn = {
    "text": Buttons.goto_main_text,
    "callback_data": Buttons.goto_main_callback,
}


@router.callback_query(F.data == Buttons.goto_main_callback, StateFilter(any_state))
async def goto_main(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_admin(callback_query.message, state)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    # if not await check_admin_access(message.from_user.id, db_session):
    #     return

    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.manage_channels_text,
        callback_data=Buttons.manage_channels_callback,
    )
    builder.button(
        text=Buttons.view_logs_text, callback_data=Buttons.view_logs_callback
    )
    builder.button(text=Buttons.stats_text, callback_data=Buttons.stats_callback)
    builder.adjust(1)
    await state.set_state(Admin.main)
    await message.answer("Админ-панель:", reply_markup=builder.as_markup())


@router.callback_query(F.data == Buttons.manage_channels_callback, Admin.main)
async def manage_channels(callback_query: types.CallbackQuery, state: FSMContext):
    # async with db_session.begin() as session:
    #     channels = await session.execute(select(Channel).order_by(Channel.name))
    #     channels = channels.scalars().all()
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.add_channel_text, callback_data=Buttons.add_channel_callback
    )
    builder.button(
        text=Buttons.remove_channel_text, callback_data=Buttons.remove_channel_callback
    )
    builder.button(
        text=Buttons.list_channels_text, callback_data=Buttons.list_channels_callback
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await callback_query.message.edit_text(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await state.update_data(main_message=callback_query)
    await callback_query.answer()


@router.callback_query(F.data == Buttons.add_channel_callback, Admin.main)
async def add_channel(callback_query: types.CallbackQuery, state: FSMContext):
    pass


@router.callback_query(F.data == Buttons.remove_channel_callback, Admin.main)
async def remove_channel(callback_query: types.CallbackQuery, state: FSMContext):
    pass


@router.callback_query(F.data == Buttons.list_channels_callback, Admin.main)
async def list_channels(callback_query: types.CallbackQuery, state: FSMContext):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = [
        Channel(
            id_=119933,
            name="test1",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119934,
            name="test2",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119935,
            name="test3",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119936,
            name="test4",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119937,
            name="test5",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119938,
            name="test6",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119939,
            name="test7",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119940,
            name="test8",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119941,
            name="test9",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119942,
            name="test10",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119943,
            name="test11",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119944,
            name="test12",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119945,
            name="test13",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119946,
            name="test14",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119947,
            name="test15",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119948,
            name="test16",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119949,
            name="test17",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Channel(
            id_=119950,
            name="test18",
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=123456789,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]
    page = data.get("page", 0)
    # if not channels:
    #     stmt = select(Channel)
    #     channels = await db_session.scalars(stmt)
    #     channels = channels.all()
    #     if not channels:
    #         await callback_query.answer("Список каналов пуст", show_alert=True)
    #         return
    #     data['channels']=channels
    total_pages = len(channels) // page_size
    message_text = f"📢 Список каналов ({total_pages}):\n\n"
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
    await state.set_state(Admin.list_channels)
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(
    F.data.contains(Buttons.back_callback) | F.data.contains(Buttons.forward_callback),
    Admin.list_channels,
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
    message_text = f"📢 Список каналов ({total_pages}):\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


def get_channel_details_text(channel):
    if not channel:
        return "No details"
    return (
        f"<b>📢 Информация о канале</b>\n\n"
        f"<b>🆔 ID:</b> <code>{channel.id}</code>\n"
        f"<b>🏷 Название:</b> <code>{channel.name}</code>\n\n"
        f"<b>⚙️ Настройки:</b>\n"
        f"  • <b>Статус:</b> {'<b><u>✅ АКТИВЕН</u></b>' if channel.is_active else '❌ неактивен'}\n"
        f"  • <b>Модерация:</b> {'<b><u>✅ ВКЛЮЧЕНА</u></b>' if channel.moderation_enabled else '❌ отключена'}\n"
        f"  • <b>Уведомления:</b> <code>{channel.notification_chat_id or '❌ не настроены'}</code>\n\n"
        f"<b>📅 Даты:</b>\n"
        f"  • <b>Создан:</b> <code>{channel.created_at}</code>\n"
        f"  • <b>Обновлен:</b> <code>{channel.updated_at}</code>\n"
    )

def get_channel_details_keyboard(channel):
    builder = InlineKeyboardBuilder()
    if not channel:
        builder.button(**goto_main_menu_btn)
        builder.adjust(1)
        return builder
    builder.button(text="Изменить имя", callback_data=f"change_name_{channel.id}")
    builder.button(text="Отключить" if channel.is_active else "Включить", callback_data=f"switch_channel_status_{channel.id}")
    builder.button(
        text="Отключить модерацию" if channel.moderation_enabled else "Включить модерацию", callback_data=f"switch_moderation_status_{channel.id}"
    )
    builder.button(
        text="Изменить чат уведомлений",
        callback_data=f"change_chat_notification_{channel.id}",
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    return builder

@router.callback_query(F.data.startswith("channel_"), Admin.list_channels)
async def channel_details(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    channel=None
    for c in channels:
        if c.id == channel_id:
            channel=c
            break
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.channel_details)
    await state.update_data(channel_id=channel_id)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("change_name"), Admin.channel_details)
async def change_channel_name_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    await main_message.message.edit_text(
        text="Введите новое название канала")
    await state.set_state(Admin.change_channel_name)


@router.message(Admin.change_channel_name)
async def change_channel_name_stage_2(
    message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    main_message = data.get("main_message")
    new_name = message.text
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    channel=None
    for c in channels:
        if c.id == channel_id:
            c.name = new_name
            c.updated_at = datetime.now()
            channel=c
            break
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.channel_details)
    await state.update_data(channel_id=channel_id,channels=channels)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )
    # await bot.send_message(
    #     chat_id=message.chat.id, text=details, reply_markup=builder.as_markup()
    # )


@router.callback_query(F.data.startswith("switch_channel_status_"), Admin.channel_details)
async def switch_channel_status(
    callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.replace("switch_channel_status_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    channel=None
    for c in channels:
        if c.id == channel_id:
            c.is_active = False if c.is_active else True
            c.updated_at = datetime.now()
            channel=c
            break
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("switch_moderation_status_"), Admin.channel_details)
async def switch_moderation_status(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback_query.data.replace("switch_moderation_status_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels")
    channel=None
    for c in channels:
        if c.id == channel_id:
            c.moderation_enabled = False if c.moderation_enabled else True
            c.updated_at = datetime.now()
            channel=c
            break
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("change_chat_notification_"), Admin.channel_details)
async def change_chat_notification_stage_1(
        callback_query: types.CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    channel_id = int(callback_query.data.replace("change_chat_notification_", ""))
    await state.update_data(channel_id=channel_id)
    await main_message.message.edit_text(text="Введите новый id чата уведомлений")


@router.message(Admin.channel_details)
async def change_chat_notification_stage_2(
        message: types.Message, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    channel=None
    for c in channels:
        if c.id == channel_id:
            c.notification_chat_id=message.text
            c.updated_at = datetime.now()
            channel=c
            break
    await state.update_data(channels=channels)
    await message.delete()
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.channel_details)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())

