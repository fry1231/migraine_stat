from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
import pytz
from tzfpy import get_tzs
import datetime
import orjson

from db import crud
from db import crud
from db.models import User
from src.bot import dp, _, i18n
from src.config import logger
from src.misc.utils import change_user_language, local_to_utc, change_timezone_get_utc, \
    get_user_language, translate_country_name
import src.misc.keyboards as kb


# tz_dict = {
#     'Europe': {
#         'Ukraine': {
#             'timezones': [
#                 'Europe/Kiev',
#                 'Europe/Uzhgorod',
#                 .....
#                 ],
#             'code': 'UA'
#         },
#     },
# }
with open('src/misc/tz_dict.json') as f:
    tz_dict = orjson.loads(f.read())

code_by_country = {}
country_by_code = {}
for continent_ in tz_dict:
    for country_ in tz_dict[continent_]:
        code_by_country[country_] = tz_dict[continent_][country_]['code']
        country_by_code[tz_dict[continent_][country_]['code']] = country_


## Settings
### language (current = ru)
#   | - back
#   | - ru uk en fr es

### timezone (current = Europe/Paris)
#   | - back

### notification time (current = 14:00)
#   | - back
#   | - a.m.
#     | - 0 1 2 3 4 5 6 7 8 9 10 11
#   | - p.m.
#     | - 12 13 14 15 16 17 18 19 20 21 22 23

### notification frequency (current = 1 day)
#   | - back
#   | - 1 day
#   | - 2 days
#   | - 3 days
#   | - 1 week


# ==================================================
# Main menu
@dp.callback_query_handler(lambda c: c.data and c.data == 'back_to_settings', state='*')
@dp.message_handler(commands=['settings'], state='*')
async def change_settings(message_or_query: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    await i18n.trigger(action='pre_process_callback_query',
                       args=(message_or_query, None))  # kostyl, otherwise does not change language immediately
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('Язык 🇷🇺🇺🇦🇬🇧🇫🇷🇪🇸'), callback_data='change_lang'))
    keyboard.row(InlineKeyboardButton(_('Часовой пояс'), callback_data='change_timezone'))
    keyboard.row(InlineKeyboardButton(_('Время оповещений'), callback_data='change_notif_time'))
    keyboard.row(InlineKeyboardButton(_('Частота оповещений'), callback_data='change_notif_freq'))

    user: User = await crud.get_user(telegram_id=message_or_query.from_user.id)
    language: str = user.language
    tz_str = user.timezone
    tz = pytz.timezone(tz_str)
    # tz in "UTC+03:00" format
    utc_offset_str = datetime.datetime.now(tz).strftime('%z')
    utc_offset_str = f'UTC{utc_offset_str[:3]}:{utc_offset_str[3:]}'
    utc_notify_at: datetime.time = user.utc_notify_at
    local_notify_at = datetime.datetime.combine(datetime.date.today(), utc_notify_at).astimezone(tz)
    notification_time = local_notify_at.strftime('%H:%M')
    notification_period = user.notify_every
    notification_period_mapper = {
        -1: _('оповещения отключены'),
        1: _('ежедневно'),
        2: _('через день'),
        3: _('1 раз в 3 дня'),
        7: _('еженедельно'),
    }
    language_with_flag = {
        'ru': '🇷🇺 Русский',
        'uk': '🇺🇦 Українська',
        'en': '🇬🇧 English',
        'fr': '🇫🇷 Français',
        'es': '🇪🇸 Español'
    }
    text = _('Текущий язык: <b>{language}</b>\n'
             'Часовой пояс: <b>{timezone} {utc_offset_formatted}</b>\n'
             'Время оповещений: <b>{notification_time}</b>\n'
             'Частота оповещений: <b>{notification_period}</b>') \
        .format(language=language_with_flag[language],
                timezone=tz_str,
                utc_offset_formatted=utc_offset_str,
                notification_time=notification_time,
                notification_period=notification_period_mapper[notification_period])

    if isinstance(message_or_query, types.Message):
        message: types.Message = message_or_query
        await message.reply(text, reply_markup=keyboard)
    else:
        query: types.CallbackQuery = message_or_query
        await query.message.edit_text(text, reply_markup=keyboard)


# ==================================================
# Language (current = ru)
#   | - back
#   | - ru ua en fr es
@dp.callback_query_handler(lambda c: c.data and c.data == 'change_lang')
async def change_lang(callback_query: types.CallbackQuery):
    def kb_change_lang():
        keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.insert(InlineKeyboardButton(_('<< Назад'), callback_data=f'back_to_settings'))
        keyboard.insert(InlineKeyboardButton('🇷🇺 Русский', callback_data='change_lang_ru'))
        keyboard.insert(InlineKeyboardButton('🇺🇦 Українська', callback_data='change_lang_uk'))
        keyboard.insert(InlineKeyboardButton('🇬🇧 English', callback_data='change_lang_en'))
        keyboard.insert(InlineKeyboardButton('🇫🇷 Français', callback_data='change_lang_fr'))
        keyboard.insert(InlineKeyboardButton('🇪🇸 Español', callback_data='change_lang_es'))
        return keyboard
    await callback_query.message.edit_text(_('Выберите язык:'), reply_markup=kb_change_lang())


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change_lang_'))
async def change_lang_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    language = callback_query.data.split('_')[-1]
    await crud.change_user_props(telegram_id=user_id, language=language)
    await change_user_language(user_id, language)
    await change_settings(callback_query)


# ==================================================
# Timezone (current = Europe/Paris)
#  | - back
#  | - share geolocation
#    | - share geolocation 📍
#      | - choose from several or confirmation
#  | - choose from list
#    | - list of continents
#      | - list of countries
#        | - list of timezones
#  | - enter manually
#    | - entering manually
#      | - list of timezones

def kb_change_timezone():
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data='back_to_settings'))
    keyboard.row(InlineKeyboardButton(_('Поделиться геолокацией'), callback_data='change_timezone_geolocation'))
    keyboard.row(InlineKeyboardButton(_('Выбрать из списка'), callback_data='change_timezone_list'))
    # keyboard.insert(InlineKeyboardButton(_('Ввести вручную'), callback_data='change_timezone_manual'))
    return keyboard


@dp.callback_query_handler(lambda c: c.data and c.data == 'change_timezone')
async def change_timezone(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(_('Способ изменения часового пояса:'),
                                           reply_markup=kb_change_timezone())


# ======= Geolocation
@dp.callback_query_handler(lambda c: c.data and c.data == 'change_timezone_geolocation')
async def change_timezone_geolocation(callback_query: types.CallbackQuery):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(KeyboardButton(_('Поделиться геолокацией 📍'), request_location=True))
    await callback_query.message.reply(_('Поделиться геолокацией 📍'), reply_markup=keyboard)


@dp.message_handler(content_types=['location'])
async def change_timezone_geolocation_callback(message: types.Message):
    user_id = message.from_user.id
    user: User = await crud.get_user(telegram_id=user_id)
    tz_list: list[str] = get_tzs(message.location.longitude, message.location.latitude)
    await crud.change_user_props(telegram_id=user_id,
                                          latitude=message.location.latitude, longitude=message.location.longitude)
    if len(tz_list) == 0:
        await message.reply(_('Не удалось определить часовой пояс по геолокации, попробуйте другой способ'),
                            reply_markup=kb_change_timezone())
        logger.error(f'Could not get timezone from geolocation for user {user_id} '
                     f'(lat: {message.location.latitude},'
                     f' lon: {message.location.longitude})')
    elif len(tz_list) == 1:
        new_tz = tz_list[0]
        old_tz = user.timezone
        old_utc_time = user.utc_notify_at
        new_utc_time = change_timezone_get_utc(old_utc_time, old_tz, new_tz)
        await crud.change_user_props(telegram_id=user_id, timezone=new_tz, utc_notify_at=new_utc_time)
        await change_settings(message)
    elif len(tz_list) > 1:
        keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for tz in tz_list[:10]:
            tz_str = f"{tz} (UTC{datetime.datetime.now(pytz.timezone(tz)).strftime('%z')})"
            keyboard.row(InlineKeyboardButton(tz_str, callback_data=f'ch_tz_to_{tz}'))
        # NOTE all suggested timezones are wrong
        keyboard.row(InlineKeyboardButton(_('Нет нужного'), callback_data=f'change_timezone'))
        await message.reply(_('Найдено несколько часовых поясов, выберите нужный:'),
                            reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('ch_tz_to_'))
async def change_timezone_geolocation_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    new_tz = callback_query.data.split('_', maxsplit=4)[-1]
    user: User = await crud.get_user(telegram_id=user_id)
    old_tz = user.timezone
    old_utc_time = user.utc_notify_at
    new_utc_time = change_timezone_get_utc(old_utc_time, old_tz, new_tz)
    await crud.change_user_props(telegram_id=user_id, timezone=new_tz, utc_notify_at=new_utc_time)
    await change_settings(callback_query)


# ======= Choose in list
@dp.callback_query_handler(lambda c: c.data and c.data == 'change_timezone_list')
async def change_timezone_list(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=f'change_timezone'))
    keyboard.row(InlineKeyboardButton(_('Европа'), callback_data=f'change_tz_cont_europe'))
    keyboard.row(InlineKeyboardButton(_('Азия'), callback_data=f'change_tz_cont_asia'))
    keyboard.row(InlineKeyboardButton(_('Северная Америка'), callback_data=f'change_tz_cont_north-america'))
    keyboard.row(InlineKeyboardButton(_('Южная Америка'), callback_data=f'change_tz_cont_south-america'))
    keyboard.row(InlineKeyboardButton(_('Африка'), callback_data=f'change_tz_cont_africa'))
    keyboard.row(InlineKeyboardButton(_('Океания'), callback_data=f'change_tz_cont_oceania'))

    await callback_query.message.edit_text(_('Выберите континент:'),
                                           reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data
                                     and c.data.startswith('change_tz_cont_')
                                     and 'country' not in c.data)
async def change_timezone_list_continent(callback_query: types.CallbackQuery):
    c_data = callback_query.data
    continent = c_data.split('_')[3]
    user_language = await get_user_language(callback_query.from_user.id)
    page = 0
    try:
        page = int(c_data.split('_')[-1])
    except ValueError:
        pass
    countries = list(tz_dict[continent].keys())
    country_codes = [code_by_country[country] for country in countries]
    translations = {code: translate_country_name(code, user_language) for code in country_codes}
    sorted_codes = sorted(country_codes, key=lambda x: translations[x])

    translated_countries = [translations[code] for code in sorted_codes]
    countries = [country_by_code[code] for code in sorted_codes]
    # ^ translated_countries now aligned with countries

    translated_slice = translated_countries[page * 10: (page + 1) * 10]
    countries_rows = ''
    for i, country in enumerate(translated_slice):
        countries_rows += f'\n{i + 1}. {country}'

    callback_data_func = lambda country: f'ch_tz_cont_{continent}_country_{code_by_country[country]}'
    await callback_query.message.edit_text(
        _('Выберите страну:{countries_rows}').format(countries_rows=countries_rows)
        , reply_markup=kb.ten_things(list_of_el=countries,
                                     back_callback='back_to_settings',
                                     navigation_callback=f'change_tz_cont_{continent}',
                                     callback_data_func=callback_data_func,
                                     page=page))


# ch_tz_cont_{continent}_country_{country}_{page:optional}
@dp.callback_query_handler(lambda c: c.data
                                     and c.data.startswith('ch_tz_cont_')
                                     and 'country' in c.data)
async def change_timezone_list_country(callback_query: types.CallbackQuery):
    country_code = callback_query.data.split('_')[5]
    country = country_by_code[country_code]
    continent = callback_query.data.split('_')[3]
    tzs = tz_dict[continent][country]['timezones']
    page = 0
    try:
        page = int(callback_query.data.split('_')[-1])
    except ValueError:
        pass
    tzs_slice = tzs[page * 10: (page + 1) * 10]
    tzs_rows = ''
    for i, tz in enumerate(tzs_slice):
        utc_offset_str = datetime.datetime.now(pytz.timezone(tz)).strftime('%z')
        utc_offset_str = f'UTC{utc_offset_str[:3]}:{utc_offset_str[3:]}'
        tzs_rows += f'\n{i + 1:<3} `{tz:^30}` {utc_offset_str}'
    await callback_query.message.edit_text(
        _('Выберите часовой пояс:\n{tzs_rows}').format(tzs_rows=tzs_rows)
        , reply_markup=kb.ten_things(list_of_el=tzs,
                                     back_callback=f'change_tz_cont_{continent}',
                                     navigation_callback=f'ch_tz_cont_{continent}_country_{country_code}',
                                     callback_data_func=lambda tz: f'ch_tz_to_{tz}',
                                     page=page)
        , parse_mode='Markdown')


# ======= Enter manually
# @dp.callback_query_handler(lambda c: c.data and c.data == 'change_timezone_manual')
# async def change_timezone_manual(callback_query: types.CallbackQuery):
#     await callback_query.message.reply(_('Введите разницу во времени от UTC в формате +hhmm'
#                                          '(например, для Московского времени введите +0300)'))


# ==================================================
# Notification time (current = 14:00)
#   | - back
#   | - a.m.
#     | - 1 2 3 4 5 6 7 8 9 10 11 0
#   | - p.m.
#     | - 13 14 15 16 17 18 19 20 21 22 23 24
@dp.callback_query_handler(lambda c: c.data and c.data == 'change_notif_time')
async def change_notif_time(callback_query: types.CallbackQuery):
    """
    Change utc_notify_at attr in User instance
    """
    keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=f'back_to_settings'))
    keyboard.row(InlineKeyboardButton(_('до полудня'), callback_data='change_notif_time_am'))
    keyboard.row(InlineKeyboardButton(_('после полудня'), callback_data='change_notif_time_pm'))

    user_id = callback_query.from_user.id
    user: User = await crud.get_user(telegram_id=user_id)
    utc_notify_at: datetime.time = user.utc_notify_at
    tz = pytz.timezone(user.timezone)
    local_notify_at: str = datetime.datetime.combine(datetime.date.today(), utc_notify_at)\
                                                                              .astimezone(tz) \
                                                                              .strftime('%H:%M')
    text = _("Бот в определённое время будет спрашивать, болела ли голова.\n"
             "Когда лучше об этом спрашивать?\n"
             "<b>(Текущее время оповещений - {local_notify_at})</b>").format(local_notify_at=local_notify_at)
    await callback_query.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change_notif_time_'))
async def change_notif_hour(callback_query: types.CallbackQuery):
    def kb_change_notif_hour(callback_str: str):
        keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data=f'change_notif_time'))
        add = 0
        if callback_str.endswith('pm'):
            add = 12
        buttons = []
        for i in range(1, 13):
            i += add
            if i == 12:
                buttons.append(InlineKeyboardButton(_('12 (полдень)'), callback_data=f'change_notif_hour_12'))
            elif i == 24:
                buttons.append(InlineKeyboardButton(_('12 (полночь)'), callback_data=f'change_notif_hour_0'))
            else:
                buttons.append(InlineKeyboardButton(str(i), callback_data=f'change_notif_hour_{i}'))
        for i in range(4):
            keyboard.row(*buttons[i * 3: (i + 1) * 3])
        return keyboard

    await callback_query.message.edit_text(_('Выберите время оповещений:'),
                                           reply_markup=kb_change_notif_hour(callback_query.data))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change_notif_hour_'))
async def change_notif_hour_callback(callback_query: types.CallbackQuery):
    """

    """
    hour = int(callback_query.data.split('_')[-1])
    user_id = callback_query.from_user.id
    user: User = await crud.get_user(telegram_id=user_id)
    local_notify_at: datetime.time = datetime.time(hour, 0)
    utc_notify_at = local_to_utc(local_notify_at, user.timezone)
    await crud.change_user_props(telegram_id=user_id, utc_notify_at=utc_notify_at)
    await change_settings(callback_query)


# ==================================================
# Notification frequency (current = 1 day)
#   | - back
#   | - 1 day
#   | - 2 days
#   | - 3 days
#   | - 1 week
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('change_notif_freq'))
async def reschedule(callback_query: types.CallbackQuery):
    """
    Change notify_every attr in User instance
    """
    user_id = callback_query.from_user.id
    user: User = await crud.get_user(telegram_id=user_id)
    notification_period = user.notify_every
    period_text = str(notification_period)
    temp = {
        '1': _(' день'),
        '2': _(' дня'),
        '3': _(' дня'),
        '7': _(' дней'),
        '31': _(' день')
    }
    if notification_period == -1:
        text_notif_period = _("Текущий период оповещений пока не назначен")
    else:
        period_text += temp[period_text]
        text_notif_period = _("Текущая частота оповещения - 1 раз в {period_text}").format(period_text=period_text)
    text = _("Выбери период опроса (сообщения будут отправляться 1 раз в ...)\n{text_notif_period}").format(
        text_notif_period=text_notif_period)
    await callback_query.message.edit_text(text, reply_markup=kb.period_days('schedule', include_month=False))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('schedule'))
async def reschedule_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = int(callback_query.data.split('_')[-1])
    await crud.change_user_props(telegram_id=user_id, notify_every=n_days)
    await change_settings(callback_query)
