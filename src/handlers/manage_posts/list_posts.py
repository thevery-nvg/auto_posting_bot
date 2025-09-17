from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import get_pending_posts, get_published_posts, get_cancelled_posts
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,

)

router = Router(name="list_posts")


@router.callback_query(F.data == Buttons.list_posts_types_callback, Admin.manage_posts)
async def list_posts_types(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    main_message = data.get("main_message")

    builder = InlineKeyboardBuilder()
    builder.button(text=Buttons.pending_posts_text, callback_data=Buttons.pending_posts_callback)
    builder.button(text=Buttons.published_posts_text, callback_data=Buttons.published_posts_callback)
    builder.button(text=Buttons.cancelled_posts_text, callback_data=Buttons.cancelled_posts_callback)
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)

    await state.set_state(Admin.posts_list)
    await main_message.message.edit_text(
        "Выберите список постов:", reply_markup=builder.as_markup()
    )
@router.callback_query(F.data.contains(Buttons.pending_posts_callback)
    | F.data.contains(Buttons.published_posts_callback)
    | F.data.contains(Buttons.cancelled_posts_callback),
                       Admin.posts_list)
async def list_posts(callback_query: types.CallbackQuery, state: FSMContext, db_session: AsyncSession):
    page_size = 5
    page = 0
    data = await state.get_data()
    main_message = data.get("main_message")

    if callback_query.data == Buttons.pending_posts_callback:
        posts = await get_pending_posts(db_session)
    elif callback_query.data == Buttons.published_posts_callback:
        posts = await get_published_posts(db_session)
    else:
        posts = await get_cancelled_posts(db_session)

    message_text = f"📢 Список постов({page=}):\n\n"
    builder = InlineKeyboardBuilder()
    for post in posts[:page_size]:
        builder.button(
            text=f"{post.title}:{post.publish_time}",
            callback_data=f"post_{post.id}"
        )

    await state.update_data(page=page, posts=posts)
    if len(posts)>page_size:
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
    Admin.posts_list,
)
async def change_page(callback_query: types.CallbackQuery, state: FSMContext):
    page_size = 5
    data = await state.get_data()
    main_message = data.get("main_message")
    posts = data.get("posts")
    page = data.get("page")
    total_pages = len(posts) // page_size
    if callback_query.data == Buttons.back_callback:
        page -= 1
    if callback_query.data == Buttons.forward_callback:
        page += 1

    builder = InlineKeyboardBuilder()
    p=posts[page*page_size : page*page_size + page_size]
    n=posts[page*page_size : page*page_size + page_size+1]
    for post in p:
        builder.button(
            text=f"{post.title}:{post.publish_time}", callback_data=f"post_{post.id}"
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
        if len(n)>len(p)
        else None
    )
    navigation = [back, forward]
    builder.row(*[x for x in navigation if x])
    builder.button(**goto_main_menu_btn)
    await state.update_data(page=page, posts=posts)

    message_text = f"📢 Список постов({page=}):\n\n"
    await main_message.message.edit_text(
        text=message_text,
        reply_markup=builder.as_markup(),
    )
