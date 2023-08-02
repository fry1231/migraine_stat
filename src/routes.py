import random
import io
from src.fsm_forms import *
import src.keyboards as kb
from src.bot import dp, bot
from src.utils import notify_me, write_xlsx
from src.messages_handler import postpone_new_user_notif
from db.models import NewUser
import traceback
import logging


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Check if user exists. If not: greet and create new user.
    Save notification about new user to the message queue
    """
    user_id = message.from_user.id
    user = await crud.get_user(telegram_id=user_id)
    if not user:
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        user_name = message.from_user.username
        # Add user to the DB
        user = await crud.create_user(
            telegram_id=user_id,
            notify_every=-1,
            first_name=first_name,
            user_name=user_name
        )
        # Send the notification to the message broker
        await postpone_new_user_notif(
            NewUser(
                first_name=user.first_name,
                last_name=last_name,
                user_name=user.user_name
            )
        )
    text = \
        """Список доступных команд:
🔘 /reschedule - настроить периодичность опросов
🔘 /pain - сделать запись бо-бо
🔘 /druguse - сделать запись приёма лекарства
🔘 /check_pains - выгрузить статистику болей
🔘 /check_drugs - выгрузить статистику употребления лекарств
🔘 /add_drug - добавить используемое лекарство"""
    await message.reply(text)


@dp.message_handler(commands=['reschedule'])
async def reschedule(message: types.Message):
    """
    Change notify_every attr in User instance
    If no User instance - create one
    """
    user_id = message.from_user.id
    user = await crud.get_user(telegram_id=user_id)
    notification_period = user.notify_every
    period_text = str(notification_period)
    temp = {
        '1': ' день',
        '2': ' дня',
        '3': ' дня',
        '7': ' дней',
        '31': ' день'
    }
    if notification_period == -1:
        text_notif_period = "Текущий период оповещений пока не назначен"
    else:
        period_text += temp[period_text]
        text_notif_period = f"Текущая частота оповещения - 1 раз в {period_text}"
    text = f"Выбери период опроса (сообщения будут отправляться 1 раз в ...)\n" + text_notif_period
    await message.reply(text, reply_markup=kb.get_days_choose_kb('schedule'))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('schedule'))
async def reschedule_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = int(callback_query.data.split('_')[-1])
    await crud.reschedule(telegram_id=user_id, notify_every=n_days)
    if n_days == -1:
        await bot.send_message(user_id, f'Оповещение отключено')
    else:
        period_text = str(n_days)
        temp = {
            '1': ' день',
            '2': ' дня',
            '3': ' дня',
            '7': ' дней',
            '31': ' день'
        }
        await bot.send_message(user_id, f'Установлено оповещение раз в {n_days} {temp[period_text]}')


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
        user_druguses = await crud.get_user_druguses(user_id=user_id, period_days=n_days)
        drugs_statistics = []

        # Filling data
        for event in user_druguses:
            temp_dict = {}
            temp_dict['Лекарство'] = event.drugname
            temp_dict['Дата'] = event.datetime.strftime('%d.%m.%Y')
            temp_dict['Кол-во'] = event.amount
            drugs_statistics.append(temp_dict)

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
            # try:
            #     fig, ax = render_mpl_table(drugs_statistics)
            #     with io.BytesIO() as buf:
            #         fig.savefig(buf, format='png')
            #         buf.seek(0)
            #         await bot.send_document(user_id, types.InputFile(buf, 'drugs_statistics.png'))
            # except IndexError:
            #     await notify_me(f'User {user_id}. IndexError while get_drugs_statistics_callback'
            #                     f'\nTable size is {len(drugs_statistics)}')

            # Send Excel table
            with io.BytesIO() as buf:
                write_xlsx(buf, drugs_statistics)
                await bot.send_document(user_id, types.InputFile(buf, 'drugs_statistics.xlsx'))
        await bot.delete_message(user_id, pre_message.message_id)
    except Exception:
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
        user_paincases = await crud.get_user_pains(user_id=user_id, period_days=n_days)
        pains_statistics = []
        # Filling data
        for event in user_paincases:
            temp_dict = {}
            temp_dict['Дата'] = event.datetime.strftime('%d.%m.%Y')
            temp_dict['Часов'] = event.durability
            temp_dict['Сила'] = event.intensity
            temp_dict['Аура'] = event.aura
            temp_dict['Триггеры'] = event.provocateurs
            temp_dict['Симптомы'] = event.symptoms
            temp_dict['Примечания'] = event.description
            if len(event.medecine_taken) == 1:
                temp_dict['Лекарство'] = event.medecine_taken[0].drugname
                temp_dict['Кол-во'] = event.medecine_taken[0].amount
            else:
                temp_dict['Лекарство'] = None
                temp_dict['Кол-во'] = None
            pains_statistics.append(temp_dict)

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
                await bot.send_document(user_id, types.InputFile(buf, 'pains_statistics.xlsx'))
        await bot.delete_message(user_id, pre_message.message_id)
    except Exception:
        await notify_me(f'User {user_id}. Error while get_pain_statistics_callback'
                        f'\n\n{traceback.format_exc()}')


@dp.message_handler(commands=['download_db'])
async def get_db(message: types.Message):
    user_id = message.from_user.id
    if user_id == 358774905:
        db = types.InputFile('db/db_file/sql_app.db')
        await bot.send_document(message.from_user.id, db)


async def regular_report(user_id: int, missing_days: int):
    """
    Notify about all new users, added during the previous day
    Ask each user if there was pain during the days
    If so - start report_paincase_form
    """
    hi_s = ["Салам алейкум", "Hi", "Hello", "Ahlan wa sahlan", "Marhaba", "Hola", "Прывитанне", "Здравейте", "Jo napot",
            "Chao", "Aloha", "Hallo", "Geia sou", "Гамарджоба", "Shalom", "Selamat", "Godan daginn", "Buenas dias",
            "Buon giorno", "Ave", "Lab dien", "Sveiki", "Sveikas", "Guten Tag", "Goddag", "Dzien dobry", "Ola", "Buna",
            "Здраво", "Dobry den", "Sawatdi", "Merhaba", "Привіт", "Paivaa", "Bonjour", "Namaste", "Zdravo",
            "Dobry den", "God dag", "Saluton", "Tervist", "Konnichi wa"]
    temp = {
        '1': 'день',
        '2': 'дня',
        '3': 'дня',
        '7': 'дней',
        '31': 'день'
    }
    if str(missing_days) in temp:
        suffix = temp[str(missing_days)]
    else:
        suffix = 'дней'
    if missing_days == 1:
        text = f"{random.choice(hi_s)}! Болела ли сегодня голова?"
    else:
        text = f"{random.choice(hi_s)}! Болела ли голова за последние {missing_days} {suffix}?"
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
        results = await crud.execute_raw(text)
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

    # If I want to reply to someone
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
