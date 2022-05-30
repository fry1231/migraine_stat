from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton


schedule = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
schedule.add(InlineKeyboardButton('1 день', callback_data='schedule_1'))
schedule.add(InlineKeyboardButton('2 дня', callback_data='schedule_2'))
schedule.add(InlineKeyboardButton('3 дня', callback_data='schedule_3'))
schedule.add(InlineKeyboardButton('1 неделю', callback_data='schedule_7'))

paincase = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
paincase.add(InlineKeyboardButton('1 день', callback_data='schedule_1'))
paincase.add(InlineKeyboardButton('2 дня', callback_data='schedule_2'))
paincase.add(InlineKeyboardButton('3 дня', callback_data='schedule_3'))
paincase.add(InlineKeyboardButton('1 неделю', callback_data='schedule_7'))