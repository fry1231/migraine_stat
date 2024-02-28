from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove
from aiogram.dispatcher.filters.state import StatesGroup
from src.fsm_forms._custom import CustomState as State
from aiogram.dispatcher import FSMContext

from db import sql
from db.redis.crud import remove_user_state
from src.bot import bot, dp, _


## Pressure
### Systolic pressure
#   | - 80 - 180 (tens)
#   | - cancel
#     | - 120 121 ... 129 (ones)
#     | - cancel
### Diastolic pressure
#       | - 40 - 120 (tens)
#       | - cancel
#         | - 80 81 ... 89 (ones)
#         | - cancel
### Pulse
#           | - 40 - 120 (tens)
#           | - cancel
#             | - 80 81 ... 89 (ones)
#             | - I don't know
#             | - cancel

class ReportPressureForm(StatesGroup):
    systolic = State()
    diastolic = State()
    pulse = State()
    # owner_id


def kb_digits(values: list[int],
              by_tens: bool = False,
              add_idk: bool = False) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    # keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=back_callback))
    n_rows = len(values) // 5 + 1
    suffix = ''
    callback_suffix = 'ones'
    if by_tens:
        suffix = '..'
        callback_suffix = 'tens'
    for i in range(n_rows):
        keyboard.row(*[InlineKeyboardButton(str(val) + suffix, callback_data=f'{val}{callback_suffix}')
                       for val in values[i * 5: (i + 1) * 5]])
    if add_idk:
        keyboard.row(InlineKeyboardButton(_('Не знаю'), callback_data='idk'))
    keyboard.row(InlineKeyboardButton(_('Отмена'), callback_data=f'cancel'))
    return keyboard


### Systolic pressure
#   | - 80 - 180 (tens)
#   | - cancel
#     | - 120 121 ... 129 (ones)
#     | - cancel
@dp.message_handler(commands=['pressure'], state='*')
async def medications_entry(message: types.Message, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    empty_mes = await bot.send_message(message.from_user.id, '.', reply_markup=ReplyKeyboardRemove())
    await bot.delete_message(message.from_user.id, empty_mes.message_id)
    text = _('Бот запишет ваши показатели давления и пульса на текущий момент. \n'
             'Выберите систолическое давление (верхнее значение)')
    await ReportPressureForm.systolic.set()
    vals = list(range(80, 180, 10))
    await message.reply(text, reply_markup=kb_digits(vals, by_tens=True))


@dp.callback_query_handler(lambda c: c.data and c.data.endswith('tens'), state=ReportPressureForm.systolic)
async def process_systolic_tens(callback_query: types.CallbackQuery, state: FSMContext):
    starting_val = int(callback_query.data.replace('tens', ''))
    vals = list(range(starting_val, starting_val + 10))
    await callback_query.message.edit_reply_markup(kb_digits(vals))


### Diastolic pressure
#       | - 40 - 120 (tens)
#       | - cancel
#         | - 80 81 ... 89 (ones)
#         | - cancel
@dp.callback_query_handler(lambda c: c.data and c.data.endswith('ones'), state=ReportPressureForm.systolic)
async def process_systolic_ones(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['systolic'] = int(callback_query.data.replace('ones', ''))
    text = _('Диастолическое давление (нижнее значение):')
    vals = list(range(40, 120, 10))
    await ReportPressureForm.diastolic.set()
    await callback_query.message.edit_text(text, reply_markup=kb_digits(vals, by_tens=True))


@dp.callback_query_handler(lambda c: c.data and c.data.endswith('tens'), state=ReportPressureForm.diastolic)
async def process_diastolic_tens(callback_query: types.CallbackQuery, state: FSMContext):
    starting_val = int(callback_query.data.replace('tens', ''))
    vals = list(range(starting_val, starting_val + 10))
    await callback_query.message.edit_reply_markup(kb_digits(vals))


### Pulse
#           | - 40 - 120 (tens)
#           | - cancel
#             | - 80 81 ... 89 (ones)
#             | - I don't know
#             | - cancel
@dp.callback_query_handler(lambda c: c.data and c.data.endswith('ones'), state=ReportPressureForm.diastolic)
async def process_diastolic_ones(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        data['diastolic'] = int(callback_query.data.replace('ones', ''))
    text = _('Ваш пульс?')
    vals = list(range(40, 120, 10))
    await ReportPressureForm.pulse.set()
    keyboard = kb_digits(vals, by_tens=True, add_idk=True)
    await callback_query.message.edit_text(text, reply_markup=kb_digits(vals, by_tens=True))


@dp.callback_query_handler(lambda c: c.data and c.data.endswith('tens'), state=ReportPressureForm.pulse)
async def process_pulse_tens(callback_query: types.CallbackQuery, state: FSMContext):
    starting_val = int(callback_query.data.replace('tens', ''))
    vals = list(range(starting_val, starting_val + 10))
    await callback_query.message.edit_reply_markup(kb_digits(vals))


@dp.callback_query_handler(lambda c: c.data
                                     and (c.data.endswith('ones') or c.data == 'idk'), state=ReportPressureForm.pulse)
async def process_pulse_ones(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        if callback_query.data == 'idk':
            data['pulse'] = None
        else:
            data['pulse'] = int(callback_query.data.replace('ones', ''))
        await sql.report_pressure(systolic=data['systolic'],
                                  diastolic=data['diastolic'],
                                  pulse=data['pulse'],
                                  owner_id=callback_query.from_user.id)
    await state.finish()
    text = f"{data['systolic']}/{data['diastolic']} {data['pulse']}\n" + _("Успешно добавлено!")
    await callback_query.message.edit_text(text)
    await remove_user_state(callback_query.from_user.id)
