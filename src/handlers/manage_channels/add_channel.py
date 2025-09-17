from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import add_channel
from src.handlers.mock import Channel
from src.handlers.utils import (
    Buttons,
    Admin,
    get_channel_details_text,
    yes_no_keyboard,
    go_to_main_menu_keyboard,
)

router = Router(name="add_channel")


async def add_new_channel(data, db_session):
    name = data.get("channel_name")
    channel_id = data.get("channel_id")
    notification_id = data.get("notification_id")
    moderation_enabled = data.get("moderation_enabled")
    if moderation_enabled:
        comment_chat_id = data.get("comment_chat_id")
    else:
        comment_chat_id = None
    new_channel = Channel(
        id=channel_id,
        name=name,
        is_active=True,
        moderation_enabled=moderation_enabled,
        comment_chat_id=comment_chat_id,
        notification_chat_id=notification_id if notification_id else None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    channel = await add_channel(db_session, new_channel)
    return channel


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
        text="Нужно ли модерировать комментарии канала?", reply_markup=yes_no_keyboard()
    )


@router.callback_query(Admin.change_moderation, F.data == Buttons.yes_sure_callback)
async def add_channel_stage_5_yes(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.update_data(moderation_enabled=True)
    await state.set_state(Admin.end_add_channel)
    await main_message.message.edit_text(
        text="Введите ID канала с комментариями или перешлите сообщение из него:",
    )


@router.callback_query(Admin.change_moderation, F.data == Buttons.no_god_no_callback)
async def add_channel_stage_5_no(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    await state.update_data(moderation_enabled=False)
    data = await state.get_data()
    main_message = data.get("main_message")
    new_channel = await add_new_channel(data, db_session)
    details = get_channel_details_text(new_channel)
    await main_message.message.edit_text(
        text=f"Канал успешно добавлен!\n\n{details}",
        reply_markup=go_to_main_menu_keyboard(),
    )


@router.message(Admin.end_add_channel)
async def add_channel_stage_6(
    message: types.Message, state: FSMContext, db_session: AsyncSession
):
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
            comment_chat_id = message.forward_from_chat.id
    else:
        try:
            comment_chat_id = int(message.text)
            await message.delete()
        except ValueError:
            await message.delete()
            await main_message.message.edit_text("❌Введите корректный ID канала:")
            return
    await state.update_data(comment_chat_id=comment_chat_id)
    new_channel = await add_new_channel(data, db_session)
    details = get_channel_details_text(new_channel)
    await main_message.message.edit_text(
        text=f"Канал успешно добавлен!\n\n{details}",
        reply_markup=go_to_main_menu_keyboard(),
    )
