import asyncio
import io
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageCantBeDeleted
import traceback

from db import sql
from db.models import User, PainCase, DrugUse, Pressure
from db import sql
from src.bot import bot, dp, _
from src.config import logger
from src.misc.utils import notify_me, write_xlsx, utc_to_local


## Statistics   (DONT FORGET TO LOCALIZE EVENT TIME TO USER'S TIMEZONE)
### pain stats
#   | - back
#   | - choose a period
### medication usage
#   | - back
#   | - choose a period (1 month, 6 months, 1 year, all)
### blood pressure
#   | - back
#   | - choose a period
### generate report
#   | - back
#   | - choose a period

def days_to_period(days: int):
    """Function to ensure proper translation of period names"""
    d = {
        31: _('1 месяц'),
        183: _('6 месяцев'),
        365: _('1 год'),
        -1: _('Весь период')
    }
    return d[days]


def kb_period(callback_prefix: str):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton(_('<< Назад'), callback_data='statistics'))
    for days in [31, 183, 365]:
        keyboard.insert(InlineKeyboardButton(days_to_period(days), callback_data=f'{callback_prefix}_{days}'))
    keyboard.insert(InlineKeyboardButton(_('Весь период'), callback_data=f'{callback_prefix}_-1'))
    return keyboard


@dp.callback_query_handler(lambda c: c.data and c.data == 'statistics', state='*')
@dp.message_handler(commands=['statistics'], state='*')
async def medications_entry(message_or_query: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton(_('Статистика головных болей'), callback_data='pains_stats'))
    keyboard.row(InlineKeyboardButton(_('Статистика приёма лекарств'), callback_data='medications_stats'))
    keyboard.row(InlineKeyboardButton(_('Статистика давления'), callback_data='pressure_stats'))
    keyboard.row(InlineKeyboardButton(_('Общий отчёт PDF'), callback_data='alert_not_implemented'))
    text = _('Здесь можно выгрузить статистику по головным болям и приёму лекарств в Excel формате '
             'или сгенерировать общий отчёт в PDF')
    if isinstance(message_or_query, types.Message):
        message: types.Message = message_or_query
        await message.reply(text, reply_markup=keyboard)
    else:
        query: types.CallbackQuery = message_or_query
        await query.message.edit_text(text, reply_markup=keyboard)


### pain stats
#   | - back
#   | - choose a period
@dp.callback_query_handler(lambda c: c.data and c.data == 'pains_stats')
async def pains_stats_entry(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(_('Статистика головных болей за:')
                                           , reply_markup=kb_period('pains_stats'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('pains_stats_'))
async def get_pain_statistics_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    pre_message: types.Message | bool = await callback_query.message.edit_text(_('Собираю данные...'))
    if pre_message == True:
        logger.error(f'Could not send pre_message while get_pain_statistics_callback for user {user_id}')
        return
    try:
        n_days = int(callback_query.data.split('_')[-1])
        user_paincases: list[PainCase] = await sql.get_user_pains(user_id=user_id, period_days=n_days)
        pains_statistics = []
        # Filling data
        for event in user_paincases:
            temp_dict = {
                'Дата': event.date.strftime('%d.%m.%Y'),
                'Часов': event.durability,
                'Сила': event.intensity,
                'Аура': event.aura,
                'Триггеры': event.provocateurs,
                'Симптомы': event.symptoms
            }
            if len(event.medecine_taken) == 0:
                temp_dict['Лекарство'] = None
                temp_dict['Кол-во'] = None
                temp_dict['Примечания'] = event.description
                pains_statistics.append(temp_dict)
            else:
                sub_event: DrugUse
                for i, sub_event in enumerate(event.medecine_taken):
                    # if only one druguse - fill the fields in the same row
                    if i == 0:
                        temp_dict['Лекарство'] = sub_event.drugname
                        temp_dict['Кол-во'] = sub_event.amount
                        temp_dict['Примечания'] = event.description
                        pains_statistics.append(temp_dict)
                    # if >1: second row would be empty, except for the druguse info
                    else:
                        temp_dict = {k: None for k in ['Дата', 'Часов', 'Сила', 'Аура', 'Триггеры', 'Симптомы']}
                        temp_dict['Лекарство'] = sub_event.drugname
                        temp_dict['Кол-во'] = sub_event.amount
                        temp_dict['Примечания'] = None
                        pains_statistics.append(temp_dict)

        # Period text definition
        period_text = days_to_period(n_days)
        if len(pains_statistics) == 0:
            await pre_message.edit_text(_("В течение запрошенного периода <b>({period_text})</b> записей нет")
                                                        .format(period_text=period_text),
                                        reply_markup=InlineKeyboardMarkup(
                                            InlineKeyboardButton(_('<< Назад'), callback_data='pains_stats')
                                        ))
        elif len(pains_statistics) > 0:
            # # Send image of a table
            # try:
            #     fig, ax = render_mpl_table(pains_statistics[["Дата", "Часов", "Сила", "Аура", "Лекарство", "Кол-во"]])
            #     with io.BytesIO() as buf:
            #         fig.savefig(buf, format='png')
            #         buf.seek(0)
            #         await bot.send_document(user_id, types.InputFile(buf, 'pains_statistics.png'))
            # except IndexError:
            #     await notify_me(f'User {user_id}. IndexError while get_pain_statistics_callback'
            #                     f'\nTable size is {len(pains_statistics)}')

            # Send table as xlsx
            with io.BytesIO() as buf:
                write_xlsx(buf, pains_statistics)
                await pre_message.edit_text(_('Готово! Высылаю файл с данными...'))
                await bot.send_document(user_id, types.InputFile(buf, 'pains_statistics.xlsx'))
                logger.info(f'User {user_id}. Sent PAIN statistics for {n_days} days')
                try:
                    await bot.delete_message(user_id, pre_message.message_id)
                except MessageCantBeDeleted:
                    pass
    except asyncio.TimeoutError:
        await pre_message.edit_text(_('В данный момент сервер загружен, повторите, пожалуйста, через пару минут'))
        logger.warning(f'User {user_id}. TimeoutError while get_pain_statistics_callback, waiting request has been sent')
    except Exception:
        await pre_message.edit_text(_('Неизвестная ошибка, отчёт уже отправлен администратору'))
        logger.error(error_msg := f'User {user_id}. Error while get_pain_statistics_callback\n\n{traceback.format_exc()}')
        await notify_me(error_msg)


### medication usage
#   | - back
#   | - choose a period (1 month, 6 months, 1 year, all)
@dp.callback_query_handler(lambda c: c.data and c.data == 'medications_stats')
async def medications_stats_entry(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(_('Статистика приёма лекарств за:')
                                           , reply_markup=kb_period('medications_stats'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('medications_stats_'))
async def get_medication_statistics_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    pre_message: types.Message | bool = await callback_query.message.edit_text(_('Собираю данные...'))
    if pre_message == True:
        logger.error(f'Could not send pre_message while get_medication_statistics_callback for user {user_id}')
        return
    try:
        n_days = int(callback_query.data.split('_')[-1])
        user_druguses: list[DrugUse] = await sql.get_user_druguses(user_id=user_id, period_days=n_days)
        medications_statistics = []
        # Filling data
        for event in user_druguses:
            temp_dict = {
                'Дата': event.date.strftime('%d.%m.%Y'),
                'Лекарство': event.drugname,
                'Кол-во': event.amount
            }
            medications_statistics.append(temp_dict)
        # Period text definition
        period_text = days_to_period(n_days)
        if len(medications_statistics) == 0:
            await pre_message.edit_text(_("В течение запрошенного периода <b>({period_text})</b> записей нет")
                                                        .format(period_text=period_text),
                                        reply_markup=InlineKeyboardMarkup(
                                            InlineKeyboardButton(_('<< Назад'), callback_data='medications_stats')
                                        ))
        elif len(medications_statistics) > 0:
            # Send table as xlsx
            with io.BytesIO() as buf:
                write_xlsx(buf, medications_statistics)
                await pre_message.edit_text(_('Готово! Высылаю файл с данными...'))
                await bot.send_document(user_id, types.InputFile(buf, 'medications_statistics.xlsx'))
                logger.info(f'User {user_id}. Sent MEDICATION statistics for {n_days} days')
                try:
                    await bot.delete_message(user_id, pre_message.message_id)
                except MessageCantBeDeleted:
                    pass
    except asyncio.TimeoutError:
        await pre_message.edit_text(_('В данный момент сервер загружен, повторите, пожалуйста, через пару минут')
                                    , reply_markup=kb_period('medications_stats'))
        logger.warning(f'User {user_id}. '
                       f'TimeoutError while get_medication_statistics_callback, waiting request has been sent')
    except Exception:
        await pre_message.edit_text(_('Неизвестная ошибка, отчёт уже отправлен администратору'))
        logger.error(error_msg := f'User {user_id}. Error while get_medication_statistics_callback\n\n{traceback.format_exc()}')
        await notify_me(error_msg)


### blood pressure
#   | - back
#   | - choose a period
@dp.callback_query_handler(lambda c: c.data and c.data == 'pressure_stats')
async def pressure_stats_entry(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(_('Записи давления за:')
                                           , reply_markup=kb_period('pressure_stats'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('pressure_stats_'))
async def get_pressure_statistics_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    pre_message: types.Message | bool = await callback_query.message.edit_text(_('Собираю данные...')
                                                                              , reply_markup=kb_period('pressure_stats'))
    if pre_message == True:
        logger.error(f'Could not send pre_message while get_pressure_statistics_callback for user {user_id}')
        return
    try:
        n_days = int(callback_query.data.split('_')[-1])
        user: User = await sql.get_user(telegram_id=user_id)
        user_pressures: list[Pressure] = await sql.get_user_pressures(user_id=user_id, period_days=n_days)
        # Period text definition
        period_text = days_to_period(n_days)
        if len(user_pressures) == 0:
            await pre_message.edit_text(_("В течение запрошенного периода <b>({period_text})</b> записей нет")
                                                        .format(period_text=period_text),
                                        reply_markup=InlineKeyboardMarkup(
                                            InlineKeyboardButton(_('<< Назад'), callback_data='pressure_stats')
                                        ))
        elif len(user_pressures) > 0:
            pressure_stats = []
            for event in user_pressures:
                event_datetime = utc_to_local(event.datetime, user.timezone)
                temp_dict = {
                    'Дата': event_datetime.strftime('%d.%m.%Y'),
                    'Время': event_datetime.strftime('%H:%M'),
                    'Систолическое': event.systolic,
                    'Диастолическое': event.diastolic,
                    'Пульс': event.pulse
                }
                pressure_stats.append(temp_dict)
            # Send table as xlsx
            with io.BytesIO() as buf:
                write_xlsx(buf, pressure_stats)
                await pre_message.edit_text(_('Готово! Высылаю файл с данными...'))
                await bot.send_document(user_id, types.InputFile(buf, 'pressure_statistics.xlsx'))
                logger.info(f'User {user_id}. Sent PRESSURE statistics for {n_days} days')
                try:
                    await bot.delete_message(user_id, pre_message.message_id)
                except MessageCantBeDeleted:
                    pass
    except asyncio.TimeoutError:
        await pre_message.edit_text(_('В данный момент сервер загружен, повторите, пожалуйста, через пару минут')
                                    , reply_markup=kb_period('pressure_stats'))
        logger.warning(f'User {user_id}. '
                       f'TimeoutError while get_pressure_statistics_callback, waiting request has been sent')
    except Exception:
        await pre_message.edit_text(_('Неизвестная ошибка, отчёт уже отправлен администратору'))
        logger.error(error_msg := f'User {user_id}. Error while get_pressure_statistics_callback\n\n{traceback.format_exc()}')
        await notify_me(error_msg)


### generate report
#   | - back
#   | - choose a period
@dp.callback_query_handler(lambda c: c.data and c.data == 'generate_report')
async def generate_report_entry(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(_('Сгенерировать отчёт за:')
                                           , reply_markup=kb_period('generate_report'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('generate_report_'))
async def generate_report_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    pre_message: types.Message | bool = await callback_query.message.edit_text(_('Собираю данные...'))
    if pre_message == True:
        logger.error(f'Could not send pre_message while generate_report_callback for user {user_id}')
        return
    try:
        n_days = int(callback_query.data.split('_')[-1])
        paincases: list[PainCase] = await sql.get_user_pains(user_id=user_id, period_days=n_days)
        druguses: list[DrugUse] = await sql.get_user_druguses(user_id=user_id, period_days=n_days)

    except asyncio.TimeoutError:
        await pre_message.edit_text(_('В данный момент сервер загружен, повторите, пожалуйста, через пару минут'))
        logger.warning(f'User {user_id}. TimeoutError while generate_report_callback, waiting request has been sent')
    except Exception:
        await pre_message.edit_text(_('Неизвестная ошибка, отчёт уже отправлен администратору'))
        logger.error(error_msg := f'User {user_id}. Error while generate_report_callback\n\n{traceback.format_exc()}')
        await notify_me(error_msg)