from aiogram import Bot, Dispatcher, types
from db import crud, models
from db.models import User, DrugUse, PainCase, Drug
from db.database import SessionLocal, engine
import src.keyboards as kb


models.Base.metadata.create_all(bind=engine)

API_TOKEN = '5494735949:AAF9NFfm2skBPjB_Z7LN8WmHUQsV8ofciXQ'

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
session = SessionLocal


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
    🔘 /missing_pain - сделать запись бо-бо за прошедшие дни
    🔘 /missing_druguse - сделать запись использования лекарства за прошедшие дни
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
    await message.reply(text, reply_markup=kb.schedule)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('schedule'))
async def reschedule_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = callback_query.data[-1]
    if n_days.isdigit():
        n_days = int(n_days)
    crud.reschedule(telegram_id=user_id, notify_every=n_days)
    await bot.send_message(user_id, f'Установлено оповещение раз в {n_days} дней')


@dp.message_handler(commands=['pain'])
async def report_paincase(message: types.Message):
    """
    Make a commit with PainCase
    """
    user_id = message.from_user.id
    user = crud.get_user(telegram_id=user_id)
    notification_period = user.notify_every
    text = f"Выбери период опроса (сообщения будут отправляться 1 раз в ...)\n" \
           f"Текущий период - {notification_period} дней."
    await message.reply(text, reply_markup=kb.schedule)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('schedule'))
async def report_paincase_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    n_days = callback_query.data[-1]
    if n_days.isdigit():
        n_days = int(n_days)
    crud.reschedule(telegram_id=user_id, notify_every=n_days)
    await bot.send_message(user_id, f'Установлено оповещение раз в {n_days} дней')


@dp.message_handler()
async def echo(message: types.Message):
    # old style:
    # await bot.send_message(message.chat.id, message.text)

    await message.answer(message.text)
