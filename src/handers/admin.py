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
from src.handers.utils import is_user_admin, log_action, check_admin_access,Buttons,goto_main_menu_btn,Admin
from src.handers.mock import channels as mock_channels

router = Router(name="admin")


@router.callback_query(F.data == Buttons.goto_main_callback, StateFilter(any_state))
async def goto_main(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cmd_admin(callback_query.message, state)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    data=await state.get_data()
    main_message=data.get("main_message")
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.manage_channels_text,
        callback_data=Buttons.manage_channels_callback,
    )
    builder.button(
        text=Buttons.manage_posts_text,
        callback_data=Buttons.manage_posts_callback,
    )
    builder.button(
        text=Buttons.manage_moderator_text,
        callback_data=Buttons.manage_moderator_callback,
    )
    builder.button(text=Buttons.stats_text, callback_data=Buttons.stats_callback)
    builder.button(
        text=Buttons.logs_text, callback_data=Buttons.logs_callback
    )
    builder.adjust(1)
    await state.set_state(Admin.main)
    if not main_message:
        await message.answer("Админ-панель:", reply_markup=builder.as_markup())
    else:
        await main_message.message.edit_text(text="Админ-панель:", reply_markup=builder.as_markup())




