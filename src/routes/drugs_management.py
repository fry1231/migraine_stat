from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext

from db.models import Drug
from db import crud
from src.bot import dp, _
import src.misc.keyboards as kb


## Medications
### add medicine
#   | - back
#   | - redirect to fsm_forms.add_drug_form
### delete medication (there are several common medications, which can't be deleted)
#   | - back
#   | - list of medications
#     | - back
#     | - delete confirmation

@dp.callback_query_handler(lambda c: c.data and c.data == 'medications', state='*')
@dp.message_handler(commands=['medications'], state='*')
async def medications_entry(message_or_query: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    user_id = message_or_query.from_user.id
    drugs: list[Drug] = await crud.get_drugs(owner=user_id)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(_('Добавить лекарство'), callback_data='add_medication'))
    if len(drugs) > 0:
        keyboard.add(InlineKeyboardButton(_('Удалить лекарство'), callback_data='delete_meds'))
        text = _('Список добавленных лекарств:')
        for drug in drugs:
            text += f'\n<b>{drug.name}</b>'
    else:
        text = _('Вы ещё не добавили ни одного лекарства')
    if isinstance(message_or_query, types.Message):
        message: types.Message = message_or_query
        await message.reply(text, reply_markup=keyboard)
    else:
        query: types.CallbackQuery = message_or_query
        await query.message.edit_text(text, reply_markup=keyboard)


# delete_meds_{page:optional}
@dp.callback_query_handler(lambda c: c.data and c.data == 'delete_meds')
async def delete_medication_menu(callback_query: types.Message | types.CallbackQuery):
    """
    Is available only if user has at least 1 medication
    """
    user_id = callback_query.from_user.id
    drugs: list[Drug] = await crud.get_drugs(owner=user_id)
    text = _('Удаляем лекарство под номером:')
    for i, drug in enumerate(drugs):
        text += f'\n<b>{i + 1:<3} {drug.name}</b>'
    page = 0
    try:
        page = int(callback_query.data.split('_')[-1])
    except ValueError:
        pass
    await callback_query.message.edit_text(
        text,
        reply_markup=kb.ten_things(list_of_el=drugs,
                                   back_callback='medications',
                                   navigation_callback='delete_meds',
                                   callback_data_func=lambda drug: f'delete_med_id_{drug.id}',
                                   page=page))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('delete_med_id_'))
async def delete_medication(callback_query: types.CallbackQuery):
    drug_id = int(callback_query.data.split('_')[-1])
    await crud.delete_drug(drug_id)
    await medications_entry(callback_query)
