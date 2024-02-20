import calendar
import datetime
from typing import Any, Callable
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from src.bot import _
from src.misc.utils import get_user_language, month_name


def yes_no_missing():
    keyboard = InlineKeyboardMarkup()
    keyboard.insert(InlineKeyboardButton(_('Да :('), callback_data='pain'))
    keyboard.insert(InlineKeyboardButton(_('Нет, всё хорошо! / Уже добавлено'), callback_data='nopain'))
    return keyboard


def ten_things(list_of_el: list[Any],
               back_callback: str,
               navigation_callback: str,
               callback_data_func: Callable[[Any], str],
               page: int = 0) -> InlineKeyboardMarkup:
    """
    Return keyboard with 10 buttons in 2 rows for a given medications, added by the user
    Allows to choose a thing by its number

    :param list_of_el: list of elements to iterate over
    :param back_callback: callback_data for navigating to previous menu
    :param navigation_callback: callback_data for navigation buttons, pages should be postfixed as _{page}
    :param callback_data_func: function for callback_data for each of 10 buttons, argument is an element from list_of_el
    :param page: int[Optional] page number

    :return: InlineKeyboardMarkup
    """
    # at most 10 elements in keyboard
    # otherwise provide additional row with "back", "next" and "1/3"(pages) buttons
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=back_callback))
    n_pages = len(list_of_el) // 10
    sliced_list = list_of_el[page * 10: (page + 1) * 10]
    # Filling keyboard with number buttons: 2 rows of 5 buttons max
    keyboard.row(*[
        InlineKeyboardButton(str(i + 1), callback_data=callback_data_func(el))
        for i, el in enumerate(sliced_list[:5])
    ])
    if len(sliced_list) > 5:  # Fill second row if there are more than 5 countries
        keyboard.row(*[
            InlineKeyboardButton(str(i + 6), callback_data=callback_data_func(el))
            for i, el in enumerate(sliced_list[5:])
        ])

    # If there are less than 10 elements, return keyboard
    if len(list_of_el) <= 10:
        return keyboard

    # If more, add navigation buttons
    if page > 0:
        back_callback = f'{navigation_callback}_{page - 1}'
    next_callback = f'{navigation_callback}_{page + 1}' if page < n_pages \
        else 'alert_last_page'
    keyboard.row(
        *[
            InlineKeyboardButton('⬅️', callback_data=back_callback),
            InlineKeyboardButton(f'{page + 1}/{n_pages + 1}', callback_data=f'alert_{page + 1}/{n_pages + 1}'),
            InlineKeyboardButton('➡️', callback_data=next_callback)
        ]
    )
    return keyboard


def period_days(callback_prefix, include_month=False, back_callback='back_to_settings'):
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=back_callback))
    keyboard.insert(InlineKeyboardButton(_('1 день'), callback_data=f'{callback_prefix}_1'))
    keyboard.insert(InlineKeyboardButton(_('2 дня'), callback_data=f'{callback_prefix}_2'))
    keyboard.insert(InlineKeyboardButton(_('3 дня'), callback_data=f'{callback_prefix}_3'))
    keyboard.insert(InlineKeyboardButton(_('1 неделю'), callback_data=f'{callback_prefix}_7'))
    if include_month:
        keyboard.insert(InlineKeyboardButton(_('1 месяц'), callback_data=f'{callback_prefix}_31'))
        keyboard.insert(InlineKeyboardButton(_('Весь период'), callback_data=f'{callback_prefix}_-1'))
    else:
        keyboard.row(InlineKeyboardButton(_('Отключить оповещения'), callback_data=f'{callback_prefix}_-1'))
    return keyboard


async def calendar_kb(callback_prefix: str,
                      user_id: int,
                      month: int,
                      year: int,
                      days_with_pain: list[int],
                      days_with_druguse: list[int],
                      days_with_pressures: list[int] = None) -> InlineKeyboardMarkup:
    """
    Creates a calendar for the given month and year
    Bottom row is for the navigation buttons
         January 2024
    Mo Tu We Th Fr Sa Su
     1  2  3  4  5  6  7
     8  9 10 11 12 13 14
    15 16 17 18 19 20 21
    22 23 24 25 26 27 28
    29 30 31
    <- December 2023    February 2024 ->
    empty buttons for empty days
    """
    keyboard = InlineKeyboardMarkup(row_width=7)
    # First row - month and year
    language = await get_user_language(user_id)
    keyboard.row(InlineKeyboardButton(f'{month_name(month, language)} {year}', callback_data='ignore'))
    # NOTE 2 letters for each day of the week
    keyboard.row(*[InlineKeyboardButton(day, callback_data="ignore") for day in _('Пн Вт Ср Чт Пт Сб Вс').split()])
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row = []
        for day in week:
            day_button_text = '  '
            callback_data = 'ignore'
            if day != 0:
                day_button_text = str(day)
                if days_with_pressures and day in days_with_pressures:
                    day_button_text += '°'
                if day in days_with_pain and day in days_with_druguse:
                    day_button_text += '※'
                elif day in days_with_druguse:
                    day_button_text += '⁘'
                elif day in days_with_pain:
                    day_button_text += '╳'
                date_str = datetime.date(year, month, day).strftime('%d.%m.%Y')
                if datetime.date(year, month, day) > datetime.date.today() + datetime.timedelta(days=1):
                    callback_data = f'alert_date_in_future'
                else:
                    callback_data = f'{callback_prefix}_{date_str}'
            row.append(InlineKeyboardButton(day_button_text, callback_data=callback_data))
        keyboard.row(*row)
    # Last row - navigation buttons
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    keyboard.row(
        InlineKeyboardButton(f'⬅️ {month_name(prev_month, language)} {prev_year}',
                             callback_data=f'{callback_prefix}_{prev_month}_{prev_year}_calendar'),
        InlineKeyboardButton(f'{month_name(next_month, language)} {next_year} ➡️',
                             callback_data=f'{callback_prefix}_{next_month}_{next_year}_calendar')
    )
    return keyboard
