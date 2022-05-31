import pandas as pd
import random
from aiogram import types

from tabulate import tabulate
from src.fsm_forms import *
import src.keyboards as kb
from src.bot import dp, bot
from src.utils import notify_me


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    user_id = message.from_user.id
    user = crud.get_user(telegram_id=user_id)
    if not user:
        crud.create_user(telegram_id=user_id, notify_every=-1)
        await notify_me(f'--notification\n'
                        f'Created user\n'
                        f'user_id {user_id}\n'
                        f'first_name {message.from_user.first_name}\n'
                        f'user_name {message.from_user.username}')
    text = """
    Привет! Список доступных комманд:\n
    🔘 /reschedule - настроить периодичность опросов
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


@dp.message_handler(commands=['download_db'])
async def get_db(message: types.Message):
    db = types.InputFile('./db/sql_app.db')
    await bot.send_document(message.from_user.id, db)


async def regular_report(user_id: int, missing_days: int):
    """
    Ask if there was pain during the days
    """
    hi_s = ["Салам алейкум", "Hi", "Hello", "Ahlan wa sahlan", "Marhaba", "Hola", "Прывитанне", "Здравейте", "Jo napot", "Chao", "Aloha", "Hallo", "Geia sou", "Гамарджоба", "Shalom", "Selamat", "Godan daginn", "Buenas dias", "Buon giorno", "Ave", "Lab dien", "Sveiki", "Sveikas", "Guten Tag", "Goddag", "Dzien dobry", "Ola", "Buna", "Здраво", "Dobry den", "Sawatdi", "Merhaba", "Привіт", "Paivaa", "Bonjour", "Namaste", "Zdravo", "Dobry den", "God dag", "Saluton", "Tervist", "Konnichi wa"]
    text = f"{random.choice(hi_s)}! Болела ли голова за последние(ий) {missing_days} дня/дней/день?"
    await bot.send_message(
        user_id,
        text,
        reply_markup=kb.yes_no_missing
    )


@dp.message_handler()
async def handle_other(message: types.Message):
    """
    Handle messages depending on its context
    """
    if message.text == 'Да :(':
        await add_paincase_entry(message)
    elif message.text == 'Нет, всё хорошо! / Уже добавлено':
        nice_words = ["Прекрасно", "Восхитительно", "Чудесно", "Великолепно", "Круто", "Здорово", "Дивно", "Чотко",
                      "Благодать", "Потрясающе", "Изумительно", "Роскошно", "Отменно", "Бесподобно", "Шикарно",
                      "Распрекрасно", "Прелестно", "Любо-дорого", "Похвально", "Обворожительно", "Балдёж", "Каеф",
                      "Неплохо", "Превосходно"]
        await message.reply(f'{random.choice(nice_words)}!', reply_markup=types.ReplyKeyboardRemove())
    elif message.text.lower().strip().startswith('спас'):
        await message.reply('Рад стараться)', reply_markup=types.ReplyKeyboardRemove())
