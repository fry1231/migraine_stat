from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from db import crud, models
from db.models import User, DrugUse, PainCase, Drug
from db.database import SessionLocal, engine
from tabulate import tabulate
from src.fsm_forms import *
import src.keyboards as kb
from src.bot import dp, bot
import pandas as pd


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    user_id = message.from_user.id
    user = crud.get_user(telegram_id=user_id)
    if not user:
        crud.create_user(telegram_id=user_id, notify_every=-1)

    text = """
    Привет! Список доступных комманд:\n
    🔘 /reschedule - настроить время опросов
    🔘 /pain - сделать запись бо-бо
    🔘 /druguse - сделать запись использования лекарства
    🔘 /check_drugs - узнать статистику употребления лекарств
    🔘 /check_pains - узнать статистику болей
    🔘 /add_drug - добавить используемое лекарство
    """
    await message.reply(text)


@dp.message_handler(commands=['reschedule'])
async def reschedule(message: types.Message):
    """
    Change notify_every attr in User instance
    If no User instance - create one
    """
    user_id = message.from_user.id
    user = crud.get_user(telegram_id=user_id)
    notification_period = user.notify_every
    if notification_period == -1:
        text_notif_period = "Текущий период пока не назначен."
    else:
        text_notif_period = f"Текущий период - {notification_period} дней."
    text = f"Выбери период опроса (сообщения будут отправляться 1 раз в ...)\n" + text_notif_period
    await message.reply(text, reply_markup=kb.get_days_choose_kb('schedule'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('schedule'))
async def reschedule_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = int(callback_query.data.split('_')[-1])
    crud.reschedule(telegram_id=user_id, notify_every=n_days)
    await bot.send_message(user_id, f'Установлено оповещение раз в {n_days} дней')


@dp.message_handler(commands=['check_drugs'])
async def get_drugs_statistics(message: types.Message):
    """
    Get druguse statistics
    """
    text = f"Запросить статистику за период: "
    await message.reply(text, reply_markup=kb.get_days_choose_kb('druguse', include_month=True))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('druguse'))
async def get_drugs_statistics_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = int(callback_query.data.split('_')[-1])
    user_druguses = crud.get_user_druguses(user_id=user_id, period_days=n_days)
    drugs_statistics = {
        'Лекарство': [],
        'Дата': [],
        'Кол-во': []
    }
    for event in user_druguses:
        drugs_statistics['Лекарство'].append(event.drugname)
        drugs_statistics['Дата'].append(event.datetime.strftime('%d.%m.%Y'))
        drugs_statistics['Кол-во'].append(event.amount)
    drugs_statistics = pd.DataFrame(drugs_statistics)
    text = tabulate(drugs_statistics, headers='keys', tablefmt="github")
    await bot.send_message(
        user_id,
        f'<pre>{text}</pre>',
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )


@dp.message_handler(commands=['check_pains'])
async def get_drugs_statistics(message: types.Message):
    """
    Get paincase statistics
    """
    text = f"Запросить статистику за период: "
    await message.reply(text, reply_markup=kb.get_days_choose_kb('paincase', include_month=True))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('paincase'))
async def get_drugs_statistics_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = int(callback_query.data.split('_')[-1])
    user_paincases = crud.get_user_pains(user_id=user_id, period_days=n_days)
    pains_statistics = {
        'Дата': [],
        'Часов': [],
        'Сила': [],
        'Аура': [],
        'Лекарство': [],
        'Кол-во': []
    }
    for event in user_paincases:
        pains_statistics['Дата'].append(event.datetime.strftime('%d.%m.%Y'))
        pains_statistics['Часов'].append(event.durability)
        pains_statistics['Сила'].append(event.intensity)
        pains_statistics['Аура'].append(event.aura)
        if len(event.children) == 1:
            pains_statistics['Лекарство'].append(event.children[0].drugname)
            pains_statistics['Кол-во'].append(event.children[0].amount)
        else:
            pains_statistics['Лекарство'].append(None)
            pains_statistics['Кол-во'].append(None)
    pains_statistics = pd.DataFrame(pains_statistics)
    text = tabulate(pains_statistics, headers='keys', tablefmt="github")
    await bot.send_message(
        user_id,
        f'<pre>{text}</pre>',
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=ParseMode.HTML,
    )

# @dp.message_handler()
# async def echo(message: types.Message):
#     # old style:
#     # await bot.send_message(message.chat.id, message.text)
#
#     await message.answer(message.text)
