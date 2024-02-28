from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup
from src.fsm_forms._custom import CustomState as State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.bot import dp
from src.fsm_forms import _keyboards as kb
from db import sql
from db.redis.crud import remove_user_state
from src.bot import _


class AddDrugForm(StatesGroup):
    name = State()
    daily_max = State()
    is_painkiller = State()
    is_temp_reducer = State()


@dp.callback_query_handler(lambda c: c.data and c.data == 'add_medication')
async def add_drug_entry(callback_query: types.CallbackQuery):
    """Conversation entrypoint"""
    # Set initial state
    await AddDrugForm.name.set()
    await callback_query.message.edit_text(_("Введите название медикамента:"))


def kb_amounts_inline():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(*[InlineKeyboardButton(_(str(amount)), callback_data=f'daily_max_{amount}')
                   for amount in [100, 200, 400, 500]])
    keyboard.row(*[InlineKeyboardButton(_(str(amount)), callback_data=f'daily_max_{amount}')
                   for amount in [600, 800, 1000, 2000]])
    keyboard.row(InlineKeyboardButton(_('Отмена'), callback_data='cancel'))
    return keyboard


@dp.message_handler(state=AddDrugForm.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Process drug name
    """
    async with state.proxy() as data:
        data['name'] = message.text.strip()
    await AddDrugForm.daily_max.set()
    await message.reply(_("Какова максимальная суточная доза (в мг)? - "
                        "выберите из предложенных или напишите свой вариант"),
                        reply_markup=kb_amounts_inline())


# Check daily_max. Should be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=AddDrugForm.daily_max)
async def process_daily_max_invalid(message: types.Message | types.CallbackQuery):
    """If daily_max is invalid"""
    return await message.reply(_("Количество должно быть числом, повторите ввод:"),
                                        reply_markup=kb_amounts_inline())


@dp.callback_query_handler(lambda c: c.data.startswith('daily_max_'), state=AddDrugForm.daily_max)
@dp.message_handler(lambda message: message.text.isdigit(), state=AddDrugForm.daily_max)
async def process_daily_max(message_or_query: types.Message | types.CallbackQuery, state: FSMContext):
    # Update state and data
    await AddDrugForm.is_painkiller.set()
    if isinstance(message_or_query, types.Message):
        await state.update_data(daily_max=int(message_or_query.text.strip()))
        await message_or_query.reply(_("Является обезболивающим?"), reply_markup=kb.yes_no_inline('is_painkiller'))
    else:
        await state.update_data(daily_max=int(message_or_query.data.split('_')[-1]))
        await message_or_query.message.edit_text(_("Является обезболивающим?"),
                                                 reply_markup=kb.yes_no_inline('is_painkiller'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('is_painkiller_'), state=AddDrugForm.is_painkiller)
async def process_is_painkiller(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['is_painkiller'] = True if callback_query.data.split('_')[-1] == 'yes' else False
    await AddDrugForm.is_temp_reducer.set()
    await callback_query.message.edit_text(_("Является жаропонижающим?"),
                                           reply_markup=kb.yes_no_inline('is_temp_reducer'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('is_temp_reducer_'), state=AddDrugForm.is_temp_reducer)
async def process_is_temp_reducer(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['is_temp_reducer'] = True if callback_query.data.split('_')[-1] == 'yes' else False
    await sql.add_drug(
        name=data['name'],
        daily_max=data['daily_max'],
        is_painkiller=data['is_painkiller'],
        is_temp_reducer=data['is_temp_reducer'],
        user_id=callback_query.from_user.id
    )
    await callback_query.message.edit_text(
                _('Добавлен {name}\n'
                  'Дозировка макс.: {daily_max}\n'
                  'Обезболивающее: {is_painkiller}\n'
                  'Жаропонижающее: {is_temp_reducer}').format(
                        name=data['name'],
                        daily_max=data['daily_max'],
                        is_painkiller=_('Да') if data['is_painkiller'] else _('Нет'),
                        is_temp_reducer=_('Да') if data['is_temp_reducer'] else _('Нет')
                ),
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton(_('Отлично!'), callback_data='medications')
                ),
            )
    # Finish conversation
    await state.finish()
    await remove_user_state(callback_query.from_user.id)
