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
from src.handers.utils import is_user_admin, log_action, check_admin_access,Buttons,goto_main_menu_btn,Admin
from src.handers.mock import channels as mock_channels,Channel

router = Router(name="manage_channels")


@router.callback_query(F.data == Buttons.manage_channels_callback, Admin.main)
async def manage_channels(callback_query: types.CallbackQuery, state: FSMContext):
    # async with db_session.begin() as session:
    #     channels = await session.execute(select(Channel).order_by(Channel.name))
    #     channels = channels.scalars().all()
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.add_channel_text, callback_data=Buttons.add_channel_callback)
    builder.button(text=Buttons.remove_channel_text, callback_data=Buttons.remove_channel_callback)
    builder.button(text=Buttons.list_channels_text, callback_data=Buttons.list_channels_callback)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await callback_query.message.edit_text(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await state.update_data(main_message=callback_query)
    await state.set_state(Admin.manage_channels)
    await callback_query.answer()


@router.callback_query(F.data == Buttons.add_channel_callback, Admin.manage_channels)
async def add_channel_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.add_channel_name)
    await main_message.message.edit_text(
        "Введите название канала:",
    )

@router.message(Admin.add_channel_name)
async def add_channel_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.update_data(channel_name=message.text)
    await state.set_state(Admin.add_channel_id)
    await message.delete()
    await main_message.message.edit_text(
        "Введите ID канала:",
    )

@router.message(Admin.add_channel_id)
async def add_channel_stage_3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        channel_id=int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Введите корректный ID канала:")
        return
    await state.set_state(Admin.add_notification_id)
    await state.update_data(channel_id=channel_id)
    await message.delete()
    #TODO: Добавить скип
    await main_message.message.edit_text(
        "Введите ID чата уведомлений:")

@router.message(Admin.add_notification_id)
async def add_channel_stage_4(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        notification_id=int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Введите корректный ID чата уведомлений:")
        return
    await state.update_data(notification_id=notification_id)
    await message.delete()
    name=data.get("channel_name")
    channel_id=data.get("channel_id")
    notification_id=data.get("notification_id")
    new_channel=Channel(
            id_=channel_id,
            name=name,
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=notification_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    channels=data.get("channels")
    channels.append(new_channel)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await state.update_data(channels=channels)
    details=get_channel_details_text(new_channel)
    await main_message.message.edit_text(
        text=f"Канал успешно добавлен!\n\n{details}",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == Buttons.remove_channel_callback, Admin.manage_channels)
async def remove_channel_stage_1(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_channel)
    await main_message.message.edit_text(
        "Введите ID канала:",
    )
@router.message(Admin.remove_channel)
async def remove_channel_stage_2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        channel_id=int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Введите корректный ID канала:")
        return
    channels=data.get("channels")
    channels=[channel for channel in channels if channel.id!=channel_id]
    await state.update_data(channels=channels)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text="Канал успешно удален!",
        reply_markup=builder.as_markup()
    )



@router.callback_query(F.data == Buttons.list_channels_callback, Admin.manage_channels)
async def list_channels(callback_query: types.CallbackQuery, state: FSMContext):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    #ТУТ ПОЛУЧЕНИЕ КАНАЛОВ
    channels=mock_channels

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
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(
    F.data.contains(Buttons.back_callback) | F.data.contains(Buttons.forward_callback),
    Admin.manage_channels,
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

@router.callback_query(F.data.startswith("channel_"), Admin.manage_channels)
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
    await state.update_data(channel_id=channel_id)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("change_name"), Admin.manage_channels)
async def change_channel_name_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")
    await main_message.message.edit_text(
        text="Введите новое название канала")
    await state.set_state(Admin.manage_channels_change_name)


@router.message(Admin.manage_channels_change_name)
async def change_channel_name_stage_2(
    message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    main_message = data.get("main_message")
    new_name = message.text
    await message.delete()
    channel=None
    for c in channels:
        if c.id == channel_id:
            c.name = new_name
            c.updated_at = datetime.now()
            channel=c
            break
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await state.update_data(channel_id=channel_id,channels=channels)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("switch_channel_status_"), Admin.manage_channels)
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


@router.callback_query(F.data.startswith("switch_moderation_status_"), Admin.manage_channels)
async def switch_moderation_status(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    channel_id = int(callback_query.data.replace("switch_moderation_status_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels")
    channel=None
    for i,c in enumerate(channels):
        if c.id == channel_id:
            channels[i].moderation_enabled = False if c.moderation_enabled else True
            channels[i].updated_at = datetime.now()
            channel=channels[i]
            break
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(
        text=details, reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("change_chat_notification_"), Admin.manage_channels)
async def change_chat_notification_stage_1(
        callback_query: types.CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    channel_id = int(callback_query.data.replace("change_chat_notification_", ""))
    await state.update_data(channel_id=channel_id)
    await state.set_state(Admin.manage_channels_change_notification)
    await main_message.message.edit_text(text="Введите новый ID чата уведомлений")


@router.message(Admin.manage_channels_change_notification)
async def change_chat_notification_stage_2(
        message: types.Message, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        notification_chat_id=int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(text="❌ID должен быть числом\nВведите новый ID чата уведомлений")
        return
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    channel=None
    for i,c in enumerate(channels):
        if c.id == channel_id:
            channels[i].notification_chat_id=notification_chat_id
            channels[i].updated_at = datetime.now()
            channel=channels[i]
            break
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())
