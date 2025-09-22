from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import any_state

from src.handlers.utils import Buttons, Admin, \
    main_menu_keyboard

router = Router(name="admin")


@router.callback_query(F.data == Buttons.goto_main_callback, StateFilter(any_state))
async def goto_main(callback_query: types.CallbackQuery, state: FSMContext):
    data=await state.get_data()
    main_message:types.CallbackQuery=data.get("main_message")
    if main_message:
        await main_message.message.delete()
    await cmd_admin(callback_query.message, state)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    data=await state.get_data()
    main_message=data.get("main_message")
    await state.set_state(Admin.main)
    if not main_message:
        await message.answer("Админ-панель:", reply_markup=main_menu_keyboard())
    else:
        await main_message.message.edit_text(text="Админ-панель:", reply_markup=main_menu_keyboard())




