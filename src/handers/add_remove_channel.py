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
from src.handers.mock import channels as mock_channels,Channel

router = Router(name="add_remove_channel")


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
    #TODO: Добавить скип
    await main_message.message.edit_text(
        "Введите ID чата уведомлений (0 - без уведомлений):")

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
    name=data.get("channel_name")
    channel_id=data.get("channel_id")
    new_channel=Channel(
            id_=channel_id,
            name=name,
            is_active=True,
            moderation_enabled=True,
            notification_chat_id=notification_id if notification_id else None,
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