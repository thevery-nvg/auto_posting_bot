from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.handers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,

)
from src.handers.manage_channels.add_channel import router as add_channel_router
from src.handers.manage_channels.remove_channel import router as remove_channel_router
from src.handers.manage_channels.list_channels import router as list_channels_router
from src.handers.manage_channels.view_channel import router as view_channel_router
from src.handers.mock import channels as mock_channels, Channel

router = Router(name="manage_channels")


@router.callback_query(F.data == Buttons.manage_channels_callback, Admin.main)
async def manage_channels(callback_query: types.CallbackQuery, state: FSMContext):
    # ТУТ ПОЛУЧЕНИЕ КАНАЛОВ
    channels = mock_channels
    await state.update_data(channels=channels)
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.add_channel_text, callback_data=Buttons.add_channel_callback
    )
    builder.button(
        text=Buttons.remove_channel_text, callback_data=Buttons.remove_channel_callback
    )
    builder.button(
        text=Buttons.list_channels_text, callback_data=Buttons.list_types_callback
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await callback_query.message.edit_text(
        "Управление каналами:", reply_markup=builder.as_markup()
    )
    await state.update_data(main_message=callback_query)
    await state.set_state(Admin.manage_channels)
    await callback_query.answer()



router.include_router(add_channel_router)
router.include_router(remove_channel_router)
router.include_router(list_channels_router)
router.include_router(view_channel_router)



