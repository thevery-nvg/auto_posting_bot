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
from src.handers.utils import Buttons,goto_main_menu_btn,Admin,get_channel_details_text,get_channel_details_keyboard
from src.handers.manage_channels.add_remove_channel import router as add_remove_channel_router
from src.handers.mock import channels as mock_channels,Channel

router = Router(name="manage_channels")
router.include_router(add_remove_channel_router)


@router.callback_query(F.data == Buttons.manage_channels_callback, Admin.main)
async def manage_channels(callback_query: types.CallbackQuery, state: FSMContext):
    #ТУТ ПОЛУЧЕНИЕ КАНАЛОВ
    channels=mock_channels
    await state.update_data(channels=channels)
    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.add_channel_text, callback_data=Buttons.add_channel_callback)
    builder.button(text=Buttons.remove_channel_text, callback_data=Buttons.remove_channel_callback)
    builder.button(text=Buttons.list_channels_text, callback_data=Buttons.list_types_callback)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await callback_query.message.edit_text(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await state.update_data(main_message=callback_query)
    await state.set_state(Admin.manage_channels)
    await callback_query.answer()





@router.callback_query(F.data == Buttons.list_types_callback, Admin.manage_channels)
async def select_list_type(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")

    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.all_channels_text, callback_data=Buttons.all_channels_callback)
    builder.button(text=Buttons.active_channels_text, callback_data=Buttons.active_channels_callback)
    builder.button(text=Buttons.inactive_channels_text, callback_data=Buttons.inactive_channels_callback)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await main_message.message.edit_text(
        "Выберите тип списка каналов:", reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.contains(Buttons.all_channels_callback) | F.data.contains(Buttons.active_channels_callback) | F.data.contains(Buttons.inactive_channels_callback),
                       Admin.manage_channels)
async def list_channels(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Все каналы
    """
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    channels=data.get("channels")
    if callback_query.data == Buttons.active_channels_callback:
        channels=[x for x in channels if x.is_active]
    elif callback_query.data == Buttons.inactive_channels_callback:
        channels=[x for x in channels if not x.is_active]
    page = data.get("page", 0)
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
