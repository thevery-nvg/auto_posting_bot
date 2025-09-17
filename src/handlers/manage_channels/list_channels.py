from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import get_active_channels, get_all_channels, get_inactive_channels
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
)

router = Router(name="list_channels")


@router.callback_query(F.data == Buttons.list_types_callback, Admin.manage_channels)
async def select_list_type(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")

    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.all_channels_text, callback_data=Buttons.all_channels_callback
    )
    builder.button(
        text=Buttons.active_channels_text,
        callback_data=Buttons.active_channels_callback,
    )
    builder.button(
        text=Buttons.inactive_channels_text,
        callback_data=Buttons.inactive_channels_callback,
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await main_message.message.edit_text(
        "Выберите список каналов:", reply_markup=builder.as_markup()
    )


@router.callback_query(
    F.data.contains(Buttons.all_channels_callback)
    | F.data.contains(Buttons.active_channels_callback)
    | F.data.contains(Buttons.inactive_channels_callback),
    Admin.manage_channels,
)
async def list_channels(callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    channels = data.get("channels",None)
    if not channels:
        if callback_query.data == Buttons.active_channels_callback:
            channels = await get_active_channels(db_session)
        elif callback_query.data == Buttons.inactive_channels_callback:
            channels = await get_inactive_channels(db_session)
        else:
            channels = await get_all_channels(db_session)
        await state.update_data(channels=channels)
    page = data.get("page", 0)
    total_pages = len(channels) // page_size
    message_text = f"📢 Список каналов ({total_pages=}):\n\n"

    builder = InlineKeyboardBuilder()
    for channel in channels[page : page + page_size]:
        builder.button(
            text=f"{channel.name} [{channel.id}]",
            callback_data=f"channel_{channel.id}",
        )

    await state.update_data(page=page+page_size, channels=channels)
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
    message_text = f"📢 Список каналов ({total_pages=}):\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )
