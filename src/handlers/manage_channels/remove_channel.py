from aiogram import Router, F, types
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import delete_channel
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
)

router = Router(name="remove_channel")


@router.callback_query(F.data == Buttons.remove_channel_callback, Admin.manage_channels)
async def remove_channel_stage_1(state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_channel)
    await main_message.message.edit_text(
        "Введите ID канала:",
    )


@router.message(Admin.remove_channel)
async def remove_channel_stage_2(message: types.Message, state: FSMContext, db_session: AsyncSession):
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
    channel=None
    filtered_channels = []
    for ch in channels:
        if ch.id == channel_id:
            channel = ch
        else:
            filtered_channels.append(ch)
    await state.update_data(channels=filtered_channels)
    await delete_channel(db_session, channel)
    builder = InlineKeyboardBuilder()
    builder.button(**goto_main_menu_btn)
    await main_message.message.edit_text(
        text="Канал успешно удален!", reply_markup=builder.as_markup()
    )
