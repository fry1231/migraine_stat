from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton


yes_no_missing = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
yes_no_missing.insert(KeyboardButton('Да :('))
yes_no_missing.insert(KeyboardButton('Нет, всё хорошо! / Уже добавлено'))


def get_days_choose_kb(callback_prefix, include_month=False):
    period_kb = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    period_kb.insert(InlineKeyboardButton('1 день', callback_data=f'{callback_prefix}_1'))
    period_kb.insert(InlineKeyboardButton('2 дня', callback_data=f'{callback_prefix}_2'))
    period_kb.insert(InlineKeyboardButton('3 дня', callback_data=f'{callback_prefix}_3'))
    period_kb.insert(InlineKeyboardButton('1 неделю', callback_data=f'{callback_prefix}_7'))
    if include_month:
        period_kb.insert(InlineKeyboardButton('1 месяц', callback_data=f'{callback_prefix}_31'))
        period_kb.insert(InlineKeyboardButton('Весь период', callback_data=f'{callback_prefix}_-1'))
    else:
        period_kb.row(InlineKeyboardButton('Отключить оповещения', callback_data=f'{callback_prefix}_-1'))
    return period_kb
