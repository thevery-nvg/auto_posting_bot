from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import add_channel
from src.handlers.mock import Channel
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
    get_channel_details_text,
    yes_no_keyboard,
    go_to_main_menu_keyboard,
)

router = Router(name="add_channel")


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
        "Введите ID канала или перешлите сообщение из него:",
    )


@router.message(Admin.add_channel_id)
async def add_channel_stage_3(message: types.Message, state: FSMContext):
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
    await state.set_state(Admin.add_notification_id)
    await state.update_data(channel_id=channel_id)
    await main_message.message.edit_text(
        "Введите ID чата уведомлений (0 - без уведомлений):"
    )


@router.message(Admin.add_notification_id)
async def add_channel_stage_4(message: types.Message, state: FSMContext):
    data = await state.get_data()
    main_message = data.get("main_message")
    try:
        notification_id = int(message.text)
        await message.delete()
    except ValueError:
        await message.delete()
        await main_message.message.edit_text(
            "❌Введите корректный ID чата уведомлений:"
        )
        return
    await state.update_data(notification_id=notification_id)
    await state.set_state(Admin.change_moderation)
    await main_message.message.edit_text(
        text="Нужно ли модерировать канал?", reply_markup=yes_no_keyboard()
    )


@router.message(Admin.change_moderation)
async def add_channel_stage_5(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    data = await state.get_data()
    main_message = data.get("main_message")
    name = data.get("channel_name")
    channel_id = data.get("channel_id")
    notification_id = data.get("notification_id")

    if callback_query.data == Buttons.yes_sure_callback:
        moderation_enabled = True
    else:
        moderation_enabled = False

    new_channel = Channel(
        id=channel_id,
        name=name,
        is_active=True,
        moderation_enabled=moderation_enabled,
        notification_chat_id=notification_id if notification_id else None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    await add_channel(db_session, new_channel)
    details = get_channel_details_text(new_channel)
    await main_message.message.edit_text(
        text=f"Канал успешно добавлен!\n\n{details}", reply_markup=go_to_main_menu_keyboard()
    )
