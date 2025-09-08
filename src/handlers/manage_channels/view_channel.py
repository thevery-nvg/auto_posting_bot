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

from core.crud import update_channel
from src.core.models import User, UserRole, Stat, Log
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    get_channel_details_text,
    get_channel_details_keyboard,
)

router = Router(name="view_channel")


@router.callback_query(F.data.startswith("channel_"), Admin.manage_channels)
async def channel_details(callback_query: types.CallbackQuery, state: FSMContext):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    channel = None
    for c in channels:
        if c.id == channel_id:
            channel = c
            break
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.update_data(channel_id=channel_id)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("change_name"), Admin.manage_channels)
async def change_channel_name_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await main_message.message.edit_text(text="Введите новое название канала")
    await state.set_state(Admin.manage_channels_change_name)


@router.message(Admin.manage_channels_change_name)
async def change_channel_name_stage_2(
    message: types.Message, state: FSMContext,db_session:AsyncSession
):
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    main_message = data.get("main_message")
    new_name = message.text
    await message.delete()
    channel = None
    for c in channels:
        if c.id == channel_id:
            c.name = new_name
            c.updated_at = datetime.now()
            channel = c
            break
    await update_channel(db_session,channel)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await state.update_data(channel_id=channel_id, channels=channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("switch_channel_status_"), Admin.manage_channels
)
async def switch_channel_status(callback_query: types.CallbackQuery, state: FSMContext,db_session:AsyncSession):
    channel_id = int(callback_query.data.replace("switch_channel_status_", ""))
    data = await state.get_data()
    channels = data.get("channels")
    main_message = data.get("main_message")
    channel = None
    for c in channels:
        if c.id == channel_id:
            c.is_active = False if c.is_active else True
            c.updated_at = datetime.now()
            channel = c
            break
    await update_channel(db_session, channel)
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("switch_moderation_status_"), Admin.manage_channels
)
async def switch_moderation_status(
    callback_query: types.CallbackQuery, state: FSMContext,db_session:AsyncSession
):
    channel_id = int(callback_query.data.replace("switch_moderation_status_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels")
    channel = None
    for i, c in enumerate(channels):
        if c.id == channel_id:
            channels[i].moderation_enabled = False if c.moderation_enabled else True
            channels[i].updated_at = datetime.now()
            channel = channels[i]
            break
    await update_channel(db_session, channel)
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("change_chat_notification_"), Admin.manage_channels
)
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
    message: types.Message, state: FSMContext,db_session:AsyncSession
):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        notification_chat_id = int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            text="❌ID должен быть числом\nВведите новый ID чата уведомлений"
        )
        return
    channel_id = data.get("channel_id")
    channels = data.get("channels")
    channel = None
    for i, c in enumerate(channels):
        if c.id == channel_id:
            channels[i].notification_chat_id = notification_chat_id
            channels[i].updated_at = datetime.now()
            channel = channels[i]
            break
    await update_channel(db_session, channel)
    await state.update_data(channels=channels)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())
