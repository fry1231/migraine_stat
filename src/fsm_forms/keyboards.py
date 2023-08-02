from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date, timedelta
from db import crud


drug_amount_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
drug_amount_kb.row('50', '100')
drug_amount_kb.row('200', '400', '800')
drug_amount_kb.row('1000', '1200', '2000')
drug_amount_kb.add('Cancel')


donate_amount_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
donate_amount_kb.row('100', '300')
donate_amount_kb.row('500', '1000')
donate_amount_kb.add('Cancel')


yes_no_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
yes_no_kb.row('Да', 'Нет')
yes_no_kb.add('Cancel')

add_description_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
add_description_kb.add('Не имеются')

durability_hours_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
for i in range(1, 11):
    durability_hours_kb.insert(str(i))
durability_hours_kb.add('Cancel')


def get_date_kb():
    date_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    date_kb.row('Сегодня')
    date_kb.row('Вчера', 'Позавчера')
    three_before = (date.today() - timedelta(days=3)).strftime('%d.%m.%Y')
    four_before = (date.today() - timedelta(days=4)).strftime('%d.%m.%Y')
    five_before = (date.today() - timedelta(days=5)).strftime('%d.%m.%Y')
    date_kb.row(three_before, four_before, five_before)
    date_kb.add('Cancel')
    return date_kb


async def get_drugs_kb_and_drugnames(owner: int = None,
                                     exclude: list = None,
                                     add_next: bool = False):
    drugs = await crud.get_drugs(owner)
    drugs_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    drugnames = [drug.name for drug in drugs]
    if exclude:
        drugnames = [drugname for drugname in drugnames if drugname not in exclude]
    _ = [drugs_kb.insert(name) for name in drugnames]
    if add_next:
        drugs_kb.row('Следующий вопрос')
    else:
        drugs_kb.add('Cancel')
    return drugs_kb, drugnames


def get_provocateurs_kb(exclude: list = None):
    prov_list = [
        'Стресс',
        'Разрешение стресса',
        'Пропуск приёма пищи',
        'Недостаточный сон',
        'Избыточный сон',
        'Алкоголь',
        'Яркий свет',
        'Шоколад',
        'Сыр',
        'Кофе',
        'Сильные запахи',
        'Погода',
        'Гормоны'
    ]
    provocateurs_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if exclude:
        prov_list = [el for el in prov_list if el not in exclude]
    _ = [provocateurs_kb.insert(el) for el in prov_list]
    provocateurs_kb.row('Следующий вопрос')
    return provocateurs_kb


def get_symptoms_kb(exclude: list = None):
    sympt_list = [
        'Тошнота',
        'Рвота',
        'Боль в шее',
        'Светочувствительность',
        'Чувствительность к звукам'
    ]
    symptoms_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    if exclude:
        sympt_list = [el for el in sympt_list if el not in exclude]
    _ = [symptoms_kb.insert(el) for el in sympt_list]
    symptoms_kb.row('Следующий вопрос')
    return symptoms_kb
