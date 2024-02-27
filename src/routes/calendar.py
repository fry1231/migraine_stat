from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
import datetime
import pytz

from src.bot import dp, _
from src.misc.utils import month_name
from src.misc.keyboards import calendar_kb, ten_things
from src.config import logger
from db.models import PainCase, DrugUse, Pressure
from db import sql


## Calendar
### After day is chosen
#   | - List of entries on the date (short report)
#     | - back
#     | - 10 things keyboard to choose what to delete

@dp.message_handler(commands=['calendar'], state='*')
async def calendar_entry(message: types.Message, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    user_id = message.from_user.id
    user = await sql.get_user(telegram_id=user_id)
    date_today = datetime.datetime.now(tz=pytz.timezone(user.timezone)).date()
    month, year = date_today.month, date_today.year
    user_pain_days: list[int] = await sql.user_pain_days(user_id, month, year)
    user_druguse_days: list[int] = await sql.user_druguse_days(user_id, month, year)
    text = _('Здесь можно посмотреть свои записи за определённый день и удалить их, при необходимости\n\n')
    text += _('╳ - головная боль\n'
              '⁘ - приём лекарства\n')
    text += f'<b>{month_name(month, locale_name=user.language)}</b> {year}\n'
    text += _('Количество дней с головной болью:') + f'<b> {len(user_pain_days)}</b>\n'
    text += _('Количество дней приёма лекарств:') + f'<b> {len(user_druguse_days)}</b>\n'
    await message.reply(text, reply_markup=await calendar_kb(callback_prefix='calendar',
                                                             user_id=user_id,
                                                             month=month,
                                                             year=year,
                                                             days_with_pain=user_pain_days,
                                                             days_with_druguse=user_druguse_days))


# calendar_{date}_{page:optional}
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('calendar_'), state='*')
async def show_list_on_date(callback_query: types.CallbackQuery, state: FSMContext = None):
    """
    Display list of entries on the date, allow to delete them with 10 things keyboard
    """
    def callback_data_func(el: PainCase | DrugUse | Pressure) -> str:
        if isinstance(el, PainCase):
            return f'delete_paincase_{el.id}'
        if isinstance(el, DrugUse):
            return f'delete_druguse_{el.id}'
        if isinstance(el, Pressure):
            return f'delete_pressure_{el.id}'

    def paincase_repr(paincase: PainCase) -> str:
        medicine_text = ''
        if paincase.medecine_taken:
            if len(paincase.medecine_taken) > 1:
                medicine_text += _('Приняты лекарства: {n_meds} шт.').format(n_meds=len(paincase.medecine_taken))
            else:
                medicine_text = f'+ {paincase.medecine_taken[0].drugname}'
        else:
            medicine_text = _('Без лекарств')
        return _('<b>Головная боль:</b> {durability} ч. | {intensity} из 10 | {medicine_text}').format(
            durability=paincase.durability,
            intensity=paincase.intensity,
            medicine_text=medicine_text)

    def druguse_repr(druguse: DrugUse) -> str:
        return _('<b>Приём лекарства:</b> {amount} {drugname}').format(
            drugname=druguse.drugname,
            amount=druguse.amount)

    def pressure_repr(pressure: Pressure) -> str:
        return _('<b>Давление:</b> {systolic}/{diastolic} {pulse}').format(
            systolic=pressure.systolic,
            diastolic=pressure.diastolic,
            pulse=pressure.pulse)

    date_str = callback_query.data.split('_')[1]
    page: int
    try:
        page = int(callback_query.data.split('_')[-1])
    except ValueError:
        page = 0
    date = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
    user_id = callback_query.from_user.id
    paincases = await sql.get_user_pains(user_id, date=date)
    druguses = await sql.get_user_druguses(user_id, date=date)
    pressures = await sql.get_user_pressures(user_id, date=date)
    # leave only non-assiciated druguses
    druguses = [druguse for druguse in druguses if druguse.paincase_id is None]
    items = paincases + druguses + pressures
    text = ''
    if len(items) == 0:
        text += _('Нет записей на <b>{date_str}</b>').format(date_str=date_str)
    else:
        text = _('Удаление записей за <b>{date_str}</b>').format(date_str=date_str)
        for i, item in enumerate(items):
            text += f'\n{i + 1}. '
            if isinstance(item, PainCase):
                text += paincase_repr(item)
            elif isinstance(item, DrugUse):
                text += druguse_repr(item)
            elif isinstance(item, Pressure):
                text += pressure_repr(item)
    await callback_query.message.edit_text(
        text,
        reply_markup=ten_things(
            list_of_el=items,
            back_callback=f'calendar_{date.month}_{date.year}_calendar',
            navigation_callback=f'calendar_{date_str}',
            callback_data_func=callback_data_func,
            page=page)
    )


# delete_{paincase,druguse,pressure}_{id}
@dp.callback_query_handler(lambda c: c.data
                                     and c.data.startswith('delete_')
                                     and c.data.split('_')[1] in ('paincase', 'druguse', 'pressure')
                                     and len(c.data.split('_')) == 3,
                           state='*')
async def delete_entry(callback_query: types.CallbackQuery, state: FSMContext = None):
    """
    Delete paincase or druguse
    """
    entity, entry_id = callback_query.data.split('_')[1:]
    entry_id = int(entry_id)
    obj = await sql.get_item_by_id(item_type=entity, item_id=entry_id)
    if not obj:
        await callback_query.answer(_('Запись не найдена'))
        return
    await sql.delete_item(obj)
    if isinstance(obj, Pressure):
        callback = f'calendar_{obj.datetime:%d.%m.%Y}'
    elif isinstance(obj, PainCase) or isinstance(obj, DrugUse):
        callback = f'calendar_{obj.date:%d.%m.%Y}'
    else:
        logger.error(f'Unknown object type: {type(obj)} while delete_entry')
    await callback_query.message.edit_text(_('Запись удалена'),
                                           reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton(_('<< Назад'), callback_data=callback)
    ))
