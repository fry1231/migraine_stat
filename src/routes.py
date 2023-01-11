import pandas as pd
import random
from aiogram import types
import io

from tabulate import tabulate
from src.fsm_forms import *
import src.keyboards as kb
from src.bot import dp, bot
from src.utils import notify_me, render_mpl_table
import traceback


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    user_id = message.from_user.id
    user = crud.get_user(telegram_id=user_id)
    if not user:
        first_name = message.from_user.first_name
        user_name = message.from_user.username
        crud.create_user(telegram_id=user_id,
                         notify_every=-1,
                         first_name=first_name,
                         user_name=user_name)
        await notify_me(f'--notification\n'
                        f'Created user\n'
                        f'user_id {user_id}\n'
                        f'first_name {first_name}\n'
                        f'user_name {user_name}')
    text = """
    Привет!
    Этот бот предназначен для ведения дневника головных болей.
    Он будет отслеживать, когда болела голова, какие медикаменты принимались, а также спросит про возможные триггеры и проявлявшиеся симптомы.
    Список доступных комманд:
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
    if n_days == -1:
        await bot.send_message(user_id, f'Оповещение отключено')
    else:
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
    try:
        user_id = callback_query.from_user.id
        pre_message = await bot.send_message(user_id, 'Собираю данные...')
        n_days = int(callback_query.data.split('_')[-1])
        user_druguses = crud.get_user_druguses(user_id=user_id, period_days=n_days)
        drugs_statistics = {
            'Дата': [],
            'Лекарство': [],
            'Кол-во': []
        }
        for event in user_druguses:
            drugs_statistics['Лекарство'].append(event.drugname)
            drugs_statistics['Дата'].append(event.datetime.strftime('%d.%m.%Y'))
            drugs_statistics['Кол-во'].append(event.amount)
        drugs_statistics = pd.DataFrame(drugs_statistics)
        # Period text definition
        period_text = ''
        if n_days != -1:
            period_text = str(n_days)
            temp = {
                '1': ' день',
                '2': ' дня',
                '3': ' дня',
                '7': ' дней',
                '31': ' день'
            }
            period_text += temp[period_text]
        if len(drugs_statistics) == 0:
            await bot.send_message(user_id, f"В течение запрошенного периода ({period_text}) записей нет")
        elif len(drugs_statistics) > 0:
            # Send an image of a table
            try:
                fig, ax = render_mpl_table(drugs_statistics)
                with io.BytesIO() as buf:
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    await bot.send_document(user_id, types.InputFile(buf, 'drugs_statistics.png'))
            except IndexError:
                await notify_me(f'User {user_id}. IndexError while get_drugs_statistics_callback'
                                f'\nTable size is {len(drugs_statistics)}')
            # Send Excel table
            with io.BytesIO() as buf:
                drugs_statistics.to_excel(buf)
                buf.seek(0)
                await bot.send_document(user_id, types.InputFile(buf, 'drugs_statistics.xlsx'))
        await bot.delete_message(user_id, pre_message.message_id)
    except Exception as e:
        await notify_me(f'User {user_id}. Error while get_drugs_statistics_callback'
                        f'\n\n{traceback.format_exc()}')


@dp.message_handler(commands=['check_pains'])
async def get_pain_statistics(message: types.Message):
    """
    Get paincase statistics
    """
    text = f"Запросить статистику за период: "
    await message.reply(text, reply_markup=kb.get_days_choose_kb('paincase', include_month=True))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('paincase'))
async def get_pain_statistics_callback(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        pre_message = await bot.send_message(user_id, 'Собираю данные...')
        n_days = int(callback_query.data.split('_')[-1])
        user_paincases = crud.get_user_pains(user_id=user_id, period_days=n_days)
        pains_statistics = {
            'Дата': [],
            'Часов': [],
            'Сила': [],
            'Аура': [],
            'Лекарство': [],
            'Кол-во': [],
            'Триггеры': [],
            'Симптомы': [],
            'Примечания': []
        }
        for event in user_paincases:
            pains_statistics['Дата'].append(event.datetime.strftime('%d.%m.%Y'))
            pains_statistics['Часов'].append(event.durability)
            pains_statistics['Сила'].append(event.intensity)
            pains_statistics['Аура'].append(event.aura)
            pains_statistics['Триггеры'].append(event.provocateurs)
            pains_statistics['Симптомы'].append(event.symptoms)
            pains_statistics['Примечания'].append(event.description)
            if len(event.medecine_taken) == 1:
                pains_statistics['Лекарство'].append(event.medecine_taken[0].drugname)
                pains_statistics['Кол-во'].append(event.medecine_taken[0].amount)
            else:
                pains_statistics['Лекарство'].append(None)
                pains_statistics['Кол-во'].append(None)
        pains_statistics = pd.DataFrame(pains_statistics)
        # Period text definition
        period_text = ''
        if n_days != -1:
            period_text = str(n_days)
            temp = {
                '1': ' день',
                '2': ' дня',
                '3': ' дня',
                '7': ' дней',
                '31': ' день'
            }
            period_text += temp[period_text]
        if len(pains_statistics) == 0:
            await bot.send_message(user_id, f"В течение запрошенного периода ({period_text}) записей нет")
        elif len(pains_statistics) > 0:
            try:
                fig, ax = render_mpl_table(pains_statistics[["Дата", "Часов", "Сила", "Аура", "Лекарство", "Кол-во"]])
                with io.BytesIO() as buf:
                    fig.savefig(buf, format='png')
                    buf.seek(0)
                    await bot.send_document(user_id, types.InputFile(buf, 'pains_statistics.png'))
            except IndexError:
                await notify_me(f'User {user_id}. IndexError while get_pain_statistics_callback'
                                f'\nTable size is {len(pains_statistics)}')
            with io.BytesIO() as buf:
                pains_statistics.to_excel(buf)
                buf.seek(0)
                await bot.send_document(user_id, types.InputFile(buf, 'pains_statistics.xlsx'))
        await bot.delete_message(user_id, pre_message.message_id)
    except Exception as e:
        await notify_me(f'User {user_id}. Error while get_pain_statistics_callback'
                        f'\n\n{traceback.format_exc()}')


@dp.message_handler(commands=['download_db'])
async def get_db(message: types.Message):
    user_id = message.from_user.id
    if user_id == 358774905:
        db = types.InputFile('./db/sql_app.db')
        await bot.send_document(message.from_user.id, db)


@dp.message_handler(commands=['write_polina'])
async def get_db(message: types.Message):
    text = message.text.replace('/write_polina', '').strip()
    await bot.send_message(956743055, text)


@dp.message_handler(commands=['listusers'])
async def get_db(message: types.Message):
    user_id = message.from_user.id
    if user_id == 358774905:
        users = crud.get_users()
        text = ''
        for user in users:
            text += f"""ID {user.telegram_id}
            name {user.first_name}
            tg {user.user_name}
            not {user.notify_every}
            """
        await notify_me(text)


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


@dp.message_handler(commands=['execute'])
async def execute_raw(message: types.Message):
    user_id = message.from_user.id
    if user_id == 358774905:
        text = message.text.replace('/execute', '').strip()
        results = crud.execute_raw(text)
        output = ''
        for record in results:
            if not isinstance(record, str):
                record = ", ".join([f'{k}: {v}' for k, v in record.items()])
            output += record
            output += '\n'
        await notify_me(output)


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
                      "Распрекрасно", "Прелестно", "Любо-дорого", "Похвально", "Обворожительно", "Балдёж", "Кайф",
                      "Неплохо", "Превосходно"]
        await message.reply(f'{random.choice(nice_words)}!', reply_markup=types.ReplyKeyboardRemove())
    # elif message.text.lower().strip().startswith('спасибо'):
    #     await message.reply('Рад стараться!)', reply_markup=types.ReplyKeyboardRemove())
    #     await notify_me(f'User {message.from_user.username} / {message.from_user.first_name} writes:\n'
    #                     f'{message.text}')
    elif message.from_user.id == 358774905:
        if message.reply_to_message is not None:
            message_with_credentials: types.Message = message.reply_to_message
            splitted = message_with_credentials.text.split('\n')
            user_id_row = [el for el in splitted if el.startswith('user_id=')][-1]
            user_id = int(user_id_row.replace('user_id=', ''))

            message_id_row = [el for el in splitted if el.startswith('message_id=')][-1]
            reply_message_id = int(message_id_row.replace('message_id=', ''))

            text_to_reply = message.text

            await bot.send_message(chat_id=user_id,
                                   text=text_to_reply,
                                   reply_to_message_id=reply_message_id)
            await notify_me('Message sent')
    else:
        await notify_me(f'User {message.from_user.username} / {message.from_user.first_name} '
                        f'writes:\n'
                        f'{message.text}\n\n'
                        f'user_id={message.from_user.id}\n'
                        f'message_id={message.message_id}')
