import asyncio
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import orjson
import yadisk
import traceback
import os
import random

from src.bot import dp, bot, _
from src.config import PERSISTENT_DATA_DIR, logger, MY_TG_ID
from src.misc.utils import notify_me
from db.models import User
from src.misc.filters import IsAdmin
from src.misc.db_backup import do_backup
from src.misc.service_reports import everyday_report
from db import sql


@dp.message_handler(IsAdmin(), commands=['token'], state='*')
async def update_token(message: types.Message):
    if message.text.split(' ')[-1] == '/token':
        await message.reply('Please provide a token after /token command (e.g. /token 1234567890abcdefg)')
    else:
        token = message.text.split(' ')[-1]
        # check if token is valid
        client = yadisk.AsyncClient(token=token)
        async with client:
            if not await client.check_token():
                await message.reply('Invalid token')
                return
        # if valid, save it to the file
        with open(PERSISTENT_DATA_DIR / 'yadisk_token.txt', 'w') as f:
            f.write(token)
        await message.reply('Token updated')


@dp.message_handler(IsAdmin(), commands=['backup'], state='*')
async def manual_backup(message: types.Message):
    message = await message.reply('Starting backup...')
    if await do_backup():
        await message.edit_text('Backup finished successfully')
    else:
        await message.edit_text('Backup failed, check logs')


## Announcements
### make an announcement (show translations)
#   | - back
#   | - ru
#   | - en
#   | - fr
#   | - es
#   | - uk
### send announcement (show translations)
#   | - back
#   | - choose groups to send
#     | - send to all
#     | - send to active (there is at least 1 submitted paincase)
#     | - send to super active (active in the last 30 days)
#       | - send confirmation (if some translation unavailable - send en to fr & es, ru to uk, or ru to all)
### delete announcement (show translations)
#   | - back
#   | - delete confirmation


class MakeAnnouncement(StatesGroup):
    lang = State()
    text = State()


def get_prepared_announcement() -> dict:
    """
    announcement.txt format:
    {'ru': '...', 'en': '...', 'fr': '...', 'es': '...', 'uk': '...'}
    """
    if (PERSISTENT_DATA_DIR / 'announcement.txt').exists():
        with open(PERSISTENT_DATA_DIR / 'announcement.txt', 'r') as f:
            return orjson.loads(f.read())
    return {}


def get_prepared_announcement_text() -> str:
    announcement = get_prepared_announcement()
    if len(announcement) == 0:
        return 'No announcements'
    text = 'Prepared announcement:\n'
    # Max len for the whole message = 4096
    max_len_for_transl = int(4000 / len(announcement))
    for lang, transl in announcement.items():
        text += f'<b>{lang}</b>:\n{transl[:max_len_for_transl]}\n'
    return text


def add_translation(lang: str, text: str):
    announcement = get_prepared_announcement()
    announcement[lang] = text
    with open(PERSISTENT_DATA_DIR / 'announcement.txt', 'w') as f:
        f.write(orjson.dumps(announcement).decode('utf-8'))


@dp.callback_query_handler(lambda c: c.data and c.data == 'announcements', state='*')
@dp.message_handler(IsAdmin(), commands=['announcements'], state='*')
async def announcements_entry(message_or_query: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state and await state.get_state():
        await state.finish()
    announcement_text = get_prepared_announcement_text()
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('Сделать объявление', callback_data='make_announcement'))
    keyboard.add(InlineKeyboardButton('Отправить объявление', callback_data='send_announcement'))
    keyboard.add(InlineKeyboardButton('Удалить объявление', callback_data='delete_announcement'))
    if isinstance(message_or_query, types.Message):
        message: types.Message = message_or_query
        await message.reply(announcement_text, reply_markup=keyboard)
    else:
        query: types.CallbackQuery = message_or_query
        await query.message.edit_text(announcement_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data == 'make_announcement')
async def make_announcement(query_or_message: types.CallbackQuery | types.Message):
    prep_ann = get_prepared_announcement()
    prep_langs = list(prep_ann.keys())
    n_users_by_lang = {}
    for lang in ['ru', 'en', 'fr', 'es', 'uk']:
        n_users_by_lang[lang] = len(await sql.get_users_where(language=lang))
    text = 'Choose language for the announcement\n'
    for lang, n_users in n_users_by_lang.items():
        text += f'{lang}: {n_users} users'
        if lang in prep_langs:
            text += ' <b>(prepared)</b>'
        text += '\n'
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('ru', callback_data='lang_ru'))
    keyboard.add(InlineKeyboardButton('en', callback_data='lang_en'))
    keyboard.add(InlineKeyboardButton('fr', callback_data='lang_fr'))
    keyboard.add(InlineKeyboardButton('es', callback_data='lang_es'))
    keyboard.add(InlineKeyboardButton('uk', callback_data='lang_uk'))
    keyboard.add(InlineKeyboardButton('back', callback_data='announcements'))
    if isinstance(query_or_message, types.Message):
        await query_or_message.reply(text, reply_markup=keyboard)
    else:
        await query_or_message.message.edit_text(text, reply_markup=keyboard)
    await MakeAnnouncement.lang.set()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('lang_'), state=MakeAnnouncement.lang)
async def set_lang(query: types.CallbackQuery, state: FSMContext):
    lang = query.data.split('_')[-1]
    prep_ann = get_prepared_announcement()
    prep_langs = list(prep_ann.keys())
    keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for translated_lang in prep_langs:
        keyboard.add(KeyboardButton(f'Use {translated_lang}'))
    await state.update_data(lang=lang)
    await query.message.reply(f'Language: {lang}\nSend the text for the announcement\n'
                              f'Or use the text from the prepared announcement', reply_markup=keyboard)
    await MakeAnnouncement.text.set()


@dp.message_handler(state=MakeAnnouncement.text)
async def set_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    if message.text.startswith('Use '):
        use_lang = message.text.split(' ')[-1]
        prep_ann = get_prepared_announcement()
        if use_lang in get_prepared_announcement():
            text = prep_ann[use_lang]
        else:
            await message.reply('No prepared announcement for this language')
            await state.finish()
            return
    else:
        text = message.text
    add_translation(lang, text)
    await state.finish()
    await make_announcement(message)


### send announcement (show translations)
#   | - back
#   | - choose groups to send
#     | - send to all
#     | - send to active (there is at least 1 submitted paincase)
#     | - send to super active (active in the last 30 days)
#       | - send confirmation (if some translation unavailable - send en to fr & es, ru to uk, or ru to all)

@dp.callback_query_handler(lambda c: c.data and c.data == 'send_announcement')
async def send_announcement(query: types.CallbackQuery):
    prep_ann = get_prepared_announcement()
    if len(prep_ann) == 0:
        await query.message.edit_text('No announcement to send', reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('back', callback_data='announcements')
        ))
        return
    if 'ru' not in prep_ann or 'en' not in prep_ann:
        await query.message.edit_text(f'Should provide at least en and ru\n\n'
                                      f'{get_prepared_announcement_text()}',
                                      reply_markup=InlineKeyboardMarkup().add(
                                          InlineKeyboardButton('back', callback_data='announcements')))
        return
    n_all = await sql.get_users(return_count=True)
    n_active = await sql.get_users(active=True, return_count=True)
    n_superactive = await sql.get_users(super_active=True, return_count=True)
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f'Send to all ({n_all})', callback_data='send_all'))
    keyboard.add(InlineKeyboardButton(f'Send to active ({n_active})', callback_data='send_active'))
    keyboard.add(InlineKeyboardButton(f'Send to super active ({n_superactive})', callback_data='send_superactive'))
    keyboard.add(InlineKeyboardButton('back', callback_data='announcements'))
    await query.message.edit_text(get_prepared_announcement_text() + '\n\nChoose groups to send', reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('send_') and 'confirmation' not in c.data)
async def send_announcement_to_group(query: types.CallbackQuery):
    group = query.data.split('_')[-1]
    n_users: int
    if group == 'all':
        n_users = await sql.get_users(return_count=True)
    elif group == 'active':
        n_users = await sql.get_users(active=True, return_count=True)
    elif group == 'superactive':
        n_users = await sql.get_users(super_active=True, return_count=True)
    await query.message.edit_text(f'Send to {group} ({n_users} users)?', reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton('Yes', callback_data='send_confirmation_' + group),
        InlineKeyboardButton('No', callback_data='announcements')))


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('send_confirmation_'))
async def send_announcement_confirmation(query: types.CallbackQuery):
    group = query.data.split('_')[-1]
    prep_ann = get_prepared_announcement()
    users: list[User]
    if group == 'all':
        users = await sql.get_users()
    elif group == 'active':
        users = await sql.get_users(active=True)
    elif group == 'superactive':
        users = await sql.get_users(super_active=True)
    await query.message.edit_text(f'Sending to {group} ({len(users)} users)...')
    # sending
    n_sent = 0
    for i, user in enumerate(users):
        lang = user.language
        if lang not in prep_ann:
            if lang in ['fr', 'es']:
                lang = 'en'
            else:
                lang = 'ru'
        try:
            await bot.send_message(user.telegram_id, prep_ann[lang])
            n_sent += 1
        except (BotBlocked, UserDeactivated):
            await sql.delete_user(user.telegram_id)
        except NetworkError:
            await logger.error(err := f'User {user.telegram_id} Network Error')
            await notify_me(err)
        await asyncio.sleep(0.1)
        if i % 100 == 0:
            await query.message.edit_text(f'Sending to {group} {i}/{len(users)} users...')
    await query.message.edit_text(f'Sent to {n_sent} users successfully')


### delete announcement (show translations)
#   | - back
#   | - delete confirmation

@dp.callback_query_handler(lambda c: c.data and c.data == 'delete_announcement')
async def delete_announcement(query: types.CallbackQuery):
    prep_ann = get_prepared_announcement()
    if len(prep_ann) == 0:
        await query.message.edit_text('No announcement to delete', reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('back', callback_data='announcements')
        ))
        return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('Yes', callback_data='delete_confirmation'))
    keyboard.add(InlineKeyboardButton('No', callback_data='announcements'))
    await query.message.edit_text(get_prepared_announcement_text() + '\n\nDelete announcement?', reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data and c.data == 'delete_confirmation')
async def delete_announcement_confirmation(query: types.CallbackQuery):
    with open(PERSISTENT_DATA_DIR / 'announcement.txt', 'w') as f:
        f.write('{}')
    await query.message.edit_text('Announcement deleted', reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton('back', callback_data='announcements')
    ))


@dp.message_handler(IsAdmin(), commands=['report'], state='*')
async def report(message: types.Message):
    await everyday_report(reset_old_one=False)


# /write %user_id% text
@dp.message_handler(IsAdmin(), commands=['write'], state='*')
async def write(message: types.Message):
    """
    Write a message to a user, identified by user_id
    """
    text = message.text.replace('/write', '').strip()
    user_id, text = text.split(' ', maxsplit=1)[0], text.split(' ', maxsplit=1)[1]
    try:
        user_id = int(user_id)
        user: User = await sql.get_user(telegram_id=user_id)
        if user:
            await bot.send_message(user.telegram_id, text)
            await message.reply(f'Message sent to {user_id} ({user.first_name} t.me/{user.user_name})')
        else:
            await message.reply(f'User {user_id} not found')
    except Exception:
        await message.reply(f'Error while sending message to {user_id}:\n{traceback.format_exc()}')


@dp.message_handler(IsAdmin(), commands=['maintenance_on'], state='*')
async def maintenance_on(message: types.Message):
    os.environ['MAINTENANCE'] = '1'
    await message.reply(f'Maintenance mode is {os.getenv("MAINTENANCE")}')


@dp.message_handler(IsAdmin(), commands=['maintenance_off'], state='*')
async def maintenance_off(message: types.Message):
    os.environ['MAINTENANCE'] = '0'
    await message.reply(f'Maintenance mode is {os.getenv("MAINTENANCE")}')


@dp.message_handler(IsAdmin(), commands=['trigger'], state='*')
async def trigger(message: types.Message):
    user_instance = await sql.get_user(telegram_id=MY_TG_ID)
    missing_days = 1
    hi_s = ["Салам алейкум", "Hi", "Hello", "Ahlan wa sahlan", "Marhaba", "Hola", "Прывитанне", "Здравейте", "Jo napot",
            "Chao", "Aloha", "Hallo", "Geia sou", "Гамарджоба", "Shalom", "Selamat", "Godan daginn", "Buenas dias",
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
