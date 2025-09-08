from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.handlers.manage_posts.create_post import router as create_post
from src.handlers.manage_posts.list_posts import router as list_posts
from src.handlers.manage_posts.remove_post import router as remove_post
from src.handlers.manage_posts.shedule import scheduler
from src.handlers.manage_posts.view_post import router as view_post
from src.handlers.utils import (
    Buttons,
    goto_main_menu_btn,
    Admin,
)

router = Router(name="posts_main")
router.include_router(create_post)
router.include_router(list_posts)
router.include_router(remove_post)
router.include_router(view_post)


@router.callback_query(F.data == Buttons.manage_posts_callback, Admin.main)
async def manage_posts(callback_query: types.CallbackQuery, state: FSMContext):
    main_message = callback_query
    builder = InlineKeyboardBuilder()
    builder.button(
        text=Buttons.create_post_text, callback_data=Buttons.create_post_callback
    )
    builder.button(
        text=Buttons.remove_post_text, callback_data=Buttons.remove_post_callback
    )
    builder.button(
        text=Buttons.list_posts_types_text,
        callback_data=Buttons.list_posts_types_callback,
    )
    builder.button(**goto_main_menu_btn)
    builder.adjust(1)
    await state.set_state(Admin.manage_posts)
    await state.update_data(main_message=main_message)
    await main_message.message.edit_text(
        text="📢 Выберите действие:", reply_markup=builder.as_markup()
    )


# from src.core.crud import get_pending_posts
# Запуск планировщика при старте бота
# posts = await get_pending_posts(db_session)
# for post in posts:
#     scheduler.add_job(
#         publish_post,
#         trigger=DateTrigger(run_date=post.publish_time),
#         args=[bot, post],
#         id=f"post_{post.id}",
#     )
@router.startup()
async def on_startup():
    scheduler.start()


# Остановка планировщика при завершении
@router.shutdown()
async def on_shutdown():
    scheduler.shutdown()
