from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text

from db import crud
from src.bot import dp, bot, _
from src.misc.keyboards import calendar_kb
from src.misc.utils import month_name
from src.middlewares import get_user_language


# Cancel command. It should be the first handler to be registered
@dp.callback_query_handler(lambda c: c.data and c.data == 'cancel', state='*')
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals=_('Отмена'), ignore_case=True), state='*')
@dp.message_handler(Text(equals='Cancel', ignore_case=True), state='*')
async def cancel_handler(message_or_query: types.Message | types.CallbackQuery,
                         state: FSMContext = None):
    """
    Allow user to cancel any action and remove keyboard
    """
    # Cancel state, inform user about it, remove keyboard
    if state and await state.get_state():
        await state.finish()
    if isinstance(message_or_query, types.CallbackQuery):
        message_or_query = message_or_query.message
    await message_or_query.reply(_('Отменено'), reply_markup=types.ReplyKeyboardRemove())
    await bot.delete_message(chat_id=message_or_query.chat.id, message_id=message_or_query.message_id)


@dp.callback_query_handler(lambda c: c.data and c.data == 'ignore', state='*')
async def ignore_handler(callback_query: types.CallbackQuery):
    return


# To show alerts
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('alert_'), state='*')
async def display_alert(callback_query: types.CallbackQuery):
    alert_code = callback_query.data.replace('alert_', '')
    if alert_code == 'last_page':
        text = _('Уже на последней странице')
    elif alert_code == 'date_in_future':
        text = _('Дата не может быть в будущем')
    elif alert_code == 'not_implemented':
        text = _('Функция пока не реализована')
    else:
        text = alert_code
    await callback_query.answer(text)


# @{prefix}_{month}_{year}_calendar
# prefixes: calendar (to delete pc&du), paincase, druguse (to create)
@dp.callback_query_handler(lambda c: c.data and c.data.endswith('_calendar'), state='*')
async def display_calendar(callback_query: types.CallbackQuery):
    """
    Display calendar with buttons to set paincase or druguse date
    """
    callback_prefix, month, year, __ = callback_query.data.split('_')
    month, year = int(month), int(year)
    user_id = callback_query.from_user.id
    user_pain_days: list[int] = await crud.user_pain_days(user_id, month, year)
    user_druguse_days: list[int] = await crud.user_druguse_days(user_id, month, year)
    keyboard = await calendar_kb(callback_prefix=callback_prefix,
                                 user_id=user_id,
                                 month=month,
                                 year=year,
                                 days_with_pain=user_pain_days,
                                 days_with_druguse=user_druguse_days)
    if callback_prefix == 'calendar':
        curr_user: types.User = callback_query.from_user
        text = _('Здесь можно посмотреть свои записи за определённый день и удалить их, при необходимости\n\n')
        text += f'<b>{month_name(month, locale_name= await get_user_language(curr_user))}</b> {year}\n'
        text += _('Количество дней с головной болью:') + f'<b> {len(user_pain_days)}</b>\n'
        text += _('Количество дней приёма лекарств:') + f'<b> {len(user_druguse_days)}</b>\n'
        await callback_query.message.edit_text(text)
    await callback_query.message.edit_reply_markup(keyboard)
