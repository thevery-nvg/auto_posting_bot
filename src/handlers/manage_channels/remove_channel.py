from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import delete_channel
from src.handlers.utils import (
    Buttons,
    Admin,
    go_to_main_menu_keyboard,
)

router = Router(name="remove_channel")


@router.callback_query(F.data == Buttons.remove_channel_callback, Admin.manage_channels)
async def remove_channel_stage_1(state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.remove_channel)
    await main_message.message.edit_text(
        text="Введите ID канала или перешлите сообщение из него:",
    )

@router.message(Admin.remove_channel)
async def remove_channel_stage_2(message: types.Message, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    main_message = data.get("main_message")
    if message.forward_from_chat:
        if message.forward_from_chat.type != "channel":
            await message.delete()
            await main_message.message.edit_text(
                "❌Пересланное сообщение не является каналом"
            )
            return
        else:
            await message.delete()
            channel_id = message.forward_from_chat.id
    else:
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
    for c in channels:
        if c.id == channel_id:
            channel = c
        else:
            filtered_channels.append(c)
    await state.update_data(channels=filtered_channels)
    await delete_channel(db_session, channel)
    await main_message.message.edit_text(
        text="Канал успешно удален!", reply_markup=go_to_main_menu_keyboard()
    )
