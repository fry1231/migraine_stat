from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta

from db import sql
from src.bot import _


drug_amount_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
drug_amount_kb.row('25', '50', '100')
drug_amount_kb.row('200', '400', '500')
drug_amount_kb.row('550', '800', '1000')
drug_amount_kb.add('Cancel')


donate_amount_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
donate_amount_kb.row('100', '300')
donate_amount_kb.row('500', '1000')
donate_amount_kb.add('Cancel')


def yes_no_kb():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(_('Да'), _('Нет'))
    keyboard.add('Cancel')
    return keyboard


def yes_no_inline(callback_prefix: str):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton(_('Да'), callback_data=f'{callback_prefix}_yes'),
                 InlineKeyboardButton(_('Нет'), callback_data=f'{callback_prefix}_no'))
    keyboard.row(InlineKeyboardButton(_('Отмена'), callback_data=f'cancel'))
    return keyboard


def add_description_kb():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(_('Не имеются'))
    return keyboard


def durability_kb(numbers: list = None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if numbers is None:
        for i in range(1, 11):
            kb.insert(str(i))
    else:
        for num in numbers:
            kb.insert(str(num))
    kb.add('Cancel')
    return kb


def get_date_kb(date_today: date, callback_prefix: str):
    """
    Creates a keyboard for choosing the date
    |            Today  |  Yesterday        |
    |  01.01.2024 | 02.01.2024 | 03.01.2024 |   (3 days back)
    |Choose another date %from the calendar%|
    |                 Cancel                |
    :param date_today: today's date, it's needed to take into account the time zone
    :param callback_prefix: prefix for callback data (pain or druguse)
    :return: InlineKeyboardMarkup
    """
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton(_('Сегодня'),
                             callback_data=f'{callback_prefix}_{date_today.strftime("%d.%m.%Y")}'),
        InlineKeyboardButton(_('Вчера'),
                             callback_data=f'{callback_prefix}_{(date_today - timedelta(days=1)).strftime("%d.%m.%Y")}')
    )
    row = []
    for i in range(2, 5):
        str_date = (date_today - timedelta(days=i)).strftime('%d.%m.%Y')
        row.append(InlineKeyboardButton(str_date, callback_data=f'{callback_prefix}_{str_date}'))
    keyboard.row(*row)
    keyboard.row(InlineKeyboardButton(_('Выбрать другую дату'),
                                      callback_data=f'{callback_prefix}_{date_today.month}_{date_today.year}_calendar'))
    keyboard.row(InlineKeyboardButton(_('Отмена'), callback_data=f'cancel'))
    return keyboard


async def get_drugs_kb_and_drugnames(owner: int = None,
                                     exclude: list = None,
                                     add_next: bool = False):
    drugs = await sql.get_drugs(owner)
    drugs_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    drugnames = [drug.name for drug in drugs]
    if exclude:
        drugnames = [drugname for drugname in drugnames if drugname not in exclude]
    for name in drugnames:
        drugs_kb.insert(name)
    if add_next:
        drugs_kb.row(_('Следующий вопрос'))
    else:
        drugs_kb.add(_('Отмена'))
    return drugs_kb, drugnames


def get_provocateurs_kb(exclude: list = None):
    prov_list = [
        _('Стресс'),
        _('Разрешение стресса'),
        _('Пропуск приёма пищи'),
        _('Недостаточный сон'),
        _('Избыточный сон'),
        _('Алкоголь'),
        _('Яркий свет'),
        _('Шоколад'),
        _('Сыр'),
        _('Кофе'),
        _('Сильные запахи'),
        _('Погода'),
        _('Гормоны'),
        _('Физическая нагрузка')
    ]

    provocateurs_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    if exclude:
        prov_list = [el for el in prov_list if el not in exclude]
    for el in prov_list:
        provocateurs_kb.insert(el)
    provocateurs_kb.row(_('Следующий вопрос'))
    return provocateurs_kb


def get_symptoms_kb(exclude: list = None):
    sympt_list = [
        _('Тошнота'),
        _('Рвота'),
        _('Боль в шее'),
        _('Светочувствительность'),
        _('Чувствительность к звукам')
    ]
    symptoms_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if exclude:
        sympt_list = [el for el in sympt_list if el not in exclude]
    for el in sympt_list:
        symptoms_kb.insert(el)
    symptoms_kb.row(_('Следующий вопрос'))
    return symptoms_kb
