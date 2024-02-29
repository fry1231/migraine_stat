import random
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions

from db import sql
from db.models import User
from src.bot import dp, bot, _


@dp.message_handler(commands=['start', 'help'], state='*')
async def send_welcome(message: types.Message, state: FSMContext = None):
    """
    Check if user exists. If not: greet and create new user.
    Save notification about new user in Redis
    """
    if state and await state.get_state():
        await state.finish()
    user_id = message.from_user.id
    # Reject messages from bots
    if message.from_user.is_bot:
        return
    # Get current user, if not exists - add to the DB
    user = await sql.get_user(telegram_id=user_id)
    if not user:
        # User info
        first_name = message.from_user.first_name
        user_name = message.from_user.username
        locale = message.from_user.locale
        language = locale.language
        if language not in ['ru', 'uk', 'en', 'fr', 'es']:
            language = 'en'
        # Add user to the DB
        await sql.create_user(
            telegram_id=user_id,
            first_name=first_name,
            user_name=user_name,
            language=language
        )
    text = \
        _("""Привет! Я бот для ведения дневника головных болей, приёма лекарств и давления.
    Список доступных команд:
🔘 /pain - сделать запись бо-бо
🔘 /druguse - сделать запись приёма лекарства
🔘 /pressure - записать своё давление
🔘 /medications - добавить или удалить используемое лекарство
🔘 /calendar - изменить записи в календаре
🔘 /statistics - выгрузить статистику болей или приёма лекарств
🔘 /settings - настройки языка и времени оповещений""")
    await message.reply(text)


async def regular_report(user_instance: User, missing_days: int):
    """
    Ask each user if there was pain during the days
    If so - start report_paincase_form
    """
    hi_s = ["Салам алейкум", "Hi", "Hello", "Ahlan wa sahlan", "Marhaba", "Hola", "Прывiтанне", "Здравейте", "Jo napot",
            "Chao", "Aloha", "Hallo", "Geia sou", "Gamarjoba", "Shalom", "Selamat", "Godan daginn", "¡Buenos días",
            "Buon giorno", "Ave", "Lab dien", "Sveiki", "Sveikas", "Guten Tag", "Goddag", "Dzien dobry", "Ola", "Buna",
            "Здраво", "Dobry den", "Sawatdi", "Merhaba", "Привіт", "Paivaa", "Bonjour", "Namaste", "Zdravo",
            "Dobry den", "God dag", "Saluton", "Tervist", "Konnichi wa"]
    language = user_instance.language
    temp = {
        # NOTE 1
        '1': _('день', locale=language),
        # NOTE 2
        '2': _('дня', locale=language),
        # NOTE 3
        '3': _('дня', locale=language),
        # NOTE 7
        '7': _('дней', locale=language),
        # NOTE 31
        '31': _('день', locale=language)
    }
    if str(missing_days) in temp:
        suffix = temp[str(missing_days)]
    else:
        suffix = 'дней'
    if missing_days == 1:
        text = _("{greetings}! Болела ли сегодня голова?", locale=language).format(
            greetings=random.choice(hi_s)
        )
    else:
        text = _("{greetings}! "
                 "Болела ли голова за последние {missing_days} {suffix}?", locale=language).format(
            greetings=random.choice(hi_s),
            missing_days=missing_days,
            suffix=suffix
        )
    keyboard = InlineKeyboardMarkup()
    keyboard.insert(InlineKeyboardButton(_('Да :(', locale=language), callback_data='pain'))
    keyboard.insert(
        InlineKeyboardButton(_('Нет, всё хорошо! / Уже добавлено', locale=language), callback_data='nopain'))
    await bot.send_message(
        user_instance.telegram_id,
        text,
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data and c.data == 'nopain', state='*')
async def process_no_pain(callback_query: types.CallbackQuery, state: FSMContext):
    # NOTE Give some nice words to user if the user did not have a headache. Separate by comma + space
    nice_words_str = _("Прекрасно, Восхитительно, Чудесно, Великолепно, Круто, Здорово, Дивно, Чотко, Благодать, "
                       "Потрясающе, Изумительно, Роскошно, Отменно, Бесподобно, Шикарно, Распрекрасно, Прелестно, "
                       "Любо-дорого, Похвально, Обворожительно, Балдёж, Кайф, Неплохо, Превосходно")
    nice_words = nice_words_str.split(', ')
    text = callback_query.message.text
    text += '\n\n<b>'
    text += _('Нет, всё хорошо! / Уже добавлено')
    text += '</b>'
    try:
        await callback_query.message.edit_text(text=text)
    except exceptions.MessageNotModified:
        pass
    await callback_query.message.reply(f'{random.choice(nice_words)}!', reply_markup=types.ReplyKeyboardRemove())

# For c.data == 'pain' handler in fsm_forms/report_paincase_form.py
