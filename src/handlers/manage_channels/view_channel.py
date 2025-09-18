from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from core.crud import update_channel, get_channel_by_id
from src.handlers.utils import (
    Admin,
    get_channel_details_text,
    get_channel_details_keyboard,
)

router = Router(name="view_channel")


@router.callback_query(F.data.startswith("channel_"), Admin.manage_channels)
async def channel_details(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    channel_id = int(callback_query.data.replace("channel_", ""))
    data = await state.get_data()
    main_message = data.get("main_message")
    channel = await get_channel_by_id(db_session, channel_id)
    await state.update_data(channel=channel)
    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
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
    message: types.Message, state: FSMContext, db_session: AsyncSession
):
    data = await state.get_data()
    channel = data.get("channel")
    main_message = data.get("main_message")
    new_name = message.text
    await message.delete()

    channel.name = new_name
    channel = await update_channel(db_session, channel)
    await state.update_data(channel=channel)

    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("switch_channel_status_"), Admin.manage_channels
)
async def switch_channel_status(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    data = await state.get_data()
    channel = data.get("channel")
    main_message = data.get("main_message")

    channel.is_active = False if channel.is_active else True

    channel = await update_channel(db_session, channel)
    await state.update_data(channel=channel)

    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("switch_moderation_status_"), Admin.manage_channels
)
async def switch_moderation_status(
    callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession
):
    data = await state.get_data()
    main_message = data.get("main_message")
    channel = data.get("channel")

    channel.moderation_enabled = False if channel.moderation_enabled else True

    channel = await update_channel(db_session, channel)
    await state.update_data(channel=channel)

    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("change_comment_chat_id_"), Admin.manage_channels
)
async def change_comment_chat_id_stage_1(
    callback_query: types.CallbackQuery,
    state: FSMContext,
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.change_comment_chat_id)
    await main_message.message.edit_text(
        text="Введите ID канала с комментариями или перешлите сообщение из него:",
    )


@router.message(Admin.change_comment_chat_id)
async def change_comment_chat_id_stage_2(
    message: types.Message, state: FSMContext, db_session: AsyncSession, bot: Bot
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
    channel = data.get("channel")

    channel.comment_chat_id = comment_chat_id

    channel = await update_channel(db_session, channel)
    await state.update_data(channel=channel)

    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())


@router.callback_query(
    F.data.startswith("change_chat_notification_"), Admin.manage_channels
)
async def change_chat_notification_stage_1(
    callback_query: types.CallbackQuery, state: FSMContext, bot: Bot
):
    data = await state.get_data()
    main_message = data.get("main_message")
    await state.set_state(Admin.manage_channels_change_notification)
    await main_message.message.edit_text(text="Введите новый ID чата уведомлений")


@router.message(Admin.manage_channels_change_notification)
async def change_chat_notification_stage_2(
    message: types.Message, state: FSMContext, db_session: AsyncSession
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

    channel = data.get("channel")
    channel.notification_chat_id = notification_chat_id
    channel = await update_channel(db_session, channel)
    await state.update_data(channel=channel)

    details = get_channel_details_text(channel)
    builder = get_channel_details_keyboard(channel)
    await state.set_state(Admin.manage_channels)
    await main_message.message.edit_text(text=details, reply_markup=builder.as_markup())
