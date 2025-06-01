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
from src.handers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    get_channel_details_text,
    get_channel_details_keyboard,
)
from src.handers.mock import channels as mock_channels, Channel

router = Router(name="remove_channel")



@router.callback_query(F.data == Buttons.remove_channel_callback, Admin.manage_channels)
async def remove_channel_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext
):
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
        channel_id = int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text("❌Введите корректный ID канала:")
        return
    channels = data.get("channels")
    channels = [channel for channel in channels if channel.id != channel_id]
    await state.update_data(channels=channels)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text="Канал успешно удален!", reply_markup=builder.as_markup()
    )
