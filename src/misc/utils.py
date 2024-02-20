from xlsxwriter import Workbook
import io
import datetime
import pytz
import pycountry
import gettext

from db import crud
from src.bot import bot, _
from src.config import MY_TG_ID, logger, redis_conn
from db import crud

domain = 'iso3166-1'
ru = gettext.translation(domain, pycountry.LOCALES_DIR, languages=['ru'])
uk = gettext.translation(domain, pycountry.LOCALES_DIR, languages=['uk'])
fr = gettext.translation(domain, pycountry.LOCALES_DIR, languages=['fr'])
es = gettext.translation(domain, pycountry.LOCALES_DIR, languages=['es'])
ru.install()
uk.install()
fr.install()
es.install()
_ru = ru.gettext
_uk = uk.gettext
_fr = fr.gettext
_es = es.gettext


async def notify_me(text):
    """
    Notify owner with 'text'
    Splits the message if necessary, as telegram limits messages to 4096 letters
    """
    if MY_TG_ID is None or MY_TG_ID == '':
        logger.error('MY_TG_ID is None, set it in env variables')
        return
    if len(text) > 4096:
        for pos in range(0, len(text), 4096):
            await bot.send_message(MY_TG_ID, text[pos:pos + 4096])
    else:
        await bot.send_message(MY_TG_ID, text)


async def change_user_language(user_id: str | int,
                               language: str) -> None:
    """
    Changes user language in Redis for i18n middleware
    """
    await redis_conn.set(str(user_id), language)


async def get_user_language(user_id: str | int) -> str:
    """
    Gets user language from Redis
    If not found, gets it from DB and sets in Redis
    """
    language = await redis_conn.get(str(user_id))
    if language is None:
        user = await crud.get_user(telegram_id=user_id)
        language = user.language
        await redis_conn.set(str(user_id), language)
    return language


def local_to_utc(local_time: datetime.time,
                 user_timezone: str) -> datetime.time:
    """
    Converts local time to UTC time
    """
    localized_local_time = pytz.timezone(user_timezone)\
        .localize(datetime.datetime.combine(datetime.date.today(), local_time))
    return localized_local_time.astimezone(pytz.utc).time()


def utc_to_local(utc_time: datetime.time | datetime.datetime,
                 user_timezone: str) -> datetime.time | datetime.datetime:
    """
    Converts UTC time to local time
    :param utc_time: datetime.time or datetime.datetime
    :param user_timezone: str
    :return: Result in the same type as input utc_time
    """
    if isinstance(utc_time, datetime.datetime):
        localized_utc_time = pytz.utc.localize(utc_time)
        return localized_utc_time.astimezone(pytz.timezone(user_timezone))
    elif isinstance(utc_time, datetime.time):
        localized_utc_time = pytz.utc.localize(datetime.datetime.combine(datetime.date.today(), utc_time))
        return localized_utc_time.astimezone(pytz.timezone(user_timezone)).time()
    else:
        logger.error(f"Wrong type of utc_time: {type(utc_time)}")
        return utc_time


def change_timezone_get_utc(utc_time: datetime.time,
                            prev_timezone: str,
                            new_timezone: str) -> datetime.time:
    """
    Leave hour unchanged for user, changes utc_time to match in the new_timezone
    """
    localized_utc_time = pytz.utc\
        .localize(datetime.datetime.combine(datetime.date.today(), utc_time))
    localized_old_tz_time = localized_utc_time.astimezone(pytz.timezone(prev_timezone))
    hour = localized_old_tz_time.hour
    localized_new_time = pytz.timezone(new_timezone)\
        .localize(datetime.datetime.combine(datetime.date.today(), datetime.time(hour=hour)))
    return localized_new_time.astimezone(pytz.utc).time()


# def render_mpl_table(data, col_width=3.0, row_height=0.625, font_size=14,
#                      header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
#                      bbox=[0, 0, 1, 1], header_columns=0,
#                      ax=None, **kwargs):
#     """
#     Renders an image with table from given data
#     """
#     if ax is None:
#         size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
#         fig, ax = plt.subplots(figsize=size)
#         ax.axis('off')
#
#     mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)
#
#     mpl_table.auto_set_font_size(False)
#     mpl_table.set_fontsize(font_size)
#
#     for k, cell in six.iteritems(mpl_table._cells):
#         cell.set_edgecolor(edge_color)
#         if k[0] == 0 or k[1] < header_columns:
#             cell.set_text_props(weight='bold', color='w')
#             cell.set_facecolor(header_color)
#         else:
#             cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
#     return ax.get_figure(), ax


def write_xlsx(buf: io.BytesIO,
               data: list[dict]) -> None:
    """
    Writes an xlsx file in buffer 'buf' from the given data.
    Modifies buffer inplace

    :arg data - list of dicts with column names as keys

    """
    wb = Workbook(buf)
    ws = wb.add_worksheet()

    ordered_list = list(data[0].keys())

    # Filling header
    first_row = 0
    for header in ordered_list:
        col = ordered_list.index(header)
        ws.write(first_row, col, report_cols_rename(header))

    # Filling data
    row = 1
    for el in data:
        for _key, _value in el.items():
            col = ordered_list.index(_key)
            ws.write(row, col, _value)
        row += 1
    wb.close()
    buf.seek(0)


def report_cols_rename(col: str) -> str:
    d = {
        'Дата': _('Дата'),
        'Часов': _('Часов'),
        'Сила': _('Сила'),
        'Аура': _('Аура'),
        'Триггеры': _('Триггеры'),
        'Симптомы': _('Симптомы'),
        'Лекарство': _('Лекарство'),
        'Кол-во': _('Кол-во'),
        'Примечания': _('Примечания'),
        'Время': _('Время'),
        'Систолическое': _('Систолическое'),
        'Диастолическое': _('Диастолическое'),
        'Пульс': _('Пульс')
    }
    if col not in d:
        logger.error(f"Column {col} not found in report_cols_rename while making report")
    return d.get(col, col)


def translate_country_name(country_code: str, target_language: str) -> str:
    try:
        gettext_mapper = {
            'ru': _ru,
            'uk': _uk,
            'fr': _fr,
            'es': _es,
            'en': lambda x: x
        }
        return gettext_mapper[target_language](pycountry.countries.get(alpha_2=country_code).name)
    except Exception as e:
        logger.error(f"Error while translating country name for {country_code}:\n{e}")
        return "error"


def month_name(month: int, locale_name: str) -> str:
    translations = {
        1: _('Январь', locale=locale_name),
        2: _('Февраль', locale=locale_name),
        3: _('Март', locale=locale_name),
        4: _('Апрель', locale=locale_name),
        5: _('Май', locale=locale_name),
        6: _('Июнь', locale=locale_name),
        7: _('Июль', locale=locale_name),
        8: _('Август', locale=locale_name),
        9: _('Сентябрь', locale=locale_name),
        10: _('Октябрь', locale=locale_name),
        11: _('Ноябрь', locale=locale_name),
        12: _('Декабрь', locale=locale_name)
    }
    return translations[month]
