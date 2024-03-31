from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup
from src.fsm_forms._custom import CustomState as State
from aiogram.types import ParseMode
import random
import pytz

from src.bot import dp, bot, _
from src.fsm_forms import _keyboards as kb
from src.config import logger
from db import sql
from db.redis.crud import remove_user_state
import datetime


class ReportPainCaseForm(StatesGroup):
    date = State()
    durability = State()
    intensity = State()
    aura = State()
    provocateurs = State()
    symptoms = State()
    was_medecine_taken = State()
    description = State()
    # owner_id

    # if medecine taken
    drugname = State()
    amount = State()
    # owner_id
    # paincase_id


@dp.callback_query_handler(lambda c: c.data and c.data == 'pain', state='*')
@dp.message_handler(commands=['pain'], state='*')
async def add_paincase_entry(message_or_query: types.Message | types.CallbackQuery, state: FSMContext = None):
    """Conversation entrypoint"""
    if state and await state.get_state():
        await state.finish()
    # NOTE list of frustration words. Used when user says he had a headache. Separate with '|'
    wtf_words = _('Ну вот.|Ёмаё!|Тфу!|Ого, надеюсь, не слишком сильно!|Тысяча чертей!').split('|')
    wtf_words += ['😱', '😔', '😢', '😞', '😦']
    user_id = message_or_query.from_user.id
    user = await sql.get_user(telegram_id=user_id)
    if not user:
        logger.error(f"User {user_id} not found in the database!")
    tz = user.timezone
    date_today = datetime.datetime.now(pytz.timezone(tz)).date()
    # if user.notify_every == 1:   # If everyday notification, skip the date question??
    #     await ReportPainCaseForm.durability.set()
    #     await message_or_query.reply(_("Продолжительность в часах (можно написать):"),
    #                                  reply_markup=kb.durability_kb([_('Весь день'), 2, 4, 6, 12, 16]))
    await ReportPainCaseForm.date.set()
    if isinstance(message_or_query, types.Message):
        await message_or_query.reply(_("Когда?"), reply_markup=kb.get_date_kb(date_today, 'pain'))
    else:
        await message_or_query.message.edit_text(
            random.choice(wtf_words) + ' ' + _("Когда?"),
            reply_markup=kb.get_date_kb(date_today, 'pain'),
            parse_mode=ParseMode.HTML)


@dp.callback_query_handler(state=ReportPainCaseForm.date)
async def process_datetime(callback_query: types.CallbackQuery, state: FSMContext):
    ddate = callback_query.data.split('_')[-1]
    async with state.proxy() as data:
        data['date'] = ddate
    await ReportPainCaseForm.durability.set()
    text = f'<b>{ddate}</b>\n' + _("Продолжительность в часах (можно написать):")
    await bot.send_message(callback_query.from_user.id, text,
                           reply_markup=kb.durability_kb([_('Весь день'), 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16]))
    try:
        await callback_query.message.delete()
    except Exception:
        pass


@dp.message_handler(lambda message: not message.text.isdigit() and message.text != _('Весь день'),
                    state=ReportPainCaseForm.durability)
async def process_durability_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply(_("Продолжительность должна быть числом, повторите ввод:"),
                               reply_markup=kb.durability_kb(
                                   [_('Весь день'), 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16]))


@dp.message_handler(lambda message: message.text.isdigit() or message.text == _('Весь день'),
                    state=ReportPainCaseForm.durability)
async def process_durability(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        if message.text.strip() == _('Весь день'):
            data['durability'] = 24
        else:
            durability = int(message.text.strip())
            durability = min(24*7, durability)
            durability = max(1, durability)
            data['durability'] = durability
    await ReportPainCaseForm.intensity.set()
    await message.reply(_("Интенсивность от 1 до 10:"), reply_markup=kb.durability_kb())


@dp.message_handler(lambda message: not message.text.isdigit(), state=ReportPainCaseForm.intensity)
async def process_intensity_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply(_("Интенсивность должна быть числом, повторите ввод:"), reply_markup=kb.durability_kb())


@dp.message_handler(lambda message: message.text.isdigit(), state=ReportPainCaseForm.intensity)
async def process_intensity(message: types.Message, state: FSMContext):
    # Update state and data
    intensity = int(message.text.strip())
    intensity = min(10, intensity)
    intensity = max(1, intensity)
    async with state.proxy() as data:
        data['intensity'] = intensity
    await ReportPainCaseForm.aura.set()
    await message.reply(_("Была ли аура?"), reply_markup=kb.yes_no_kb())


@dp.message_handler(lambda message: message.text not in [_("Да"), _("Нет")], state=ReportPainCaseForm.aura)
async def process_aura_invalid(message: types.Message):
    return await message.reply(_("Неверный ответ, повторите: "), reply_markup=kb.yes_no_kb())


@dp.message_handler(state=ReportPainCaseForm.aura)
async def process_aura(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['aura'] = True if message.text == _("Да") else False
    await ReportPainCaseForm.provocateurs.set()
    await message.reply(_("Выбери триггеры при наличии:"), reply_markup=kb.get_provocateurs_kb())


@dp.message_handler(state=ReportPainCaseForm.provocateurs)
async def process_provocateurs(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == _('Следующий вопрос'):
            if 'provocateurs' not in data:
                data['provocateurs'] = None
            await ReportPainCaseForm.symptoms.set()
            await message.reply(_('Были ли следующие симптомы?'),
                                reply_markup=kb.get_symptoms_kb())
        else:
            if 'provocateurs' not in data:
                data['provocateurs'] = text
            else:
                data['provocateurs'] += f', {text}'
            to_exclude = [el.strip() for el in data['provocateurs'].split(',')]
            await ReportPainCaseForm.provocateurs.set()
            await message.reply(_('Можно добавить ещё или нажать на "следующий вопрос"'),
                                reply_markup=kb.get_provocateurs_kb(exclude=to_exclude))


@dp.message_handler(state=ReportPainCaseForm.symptoms)
async def process_symptoms(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == _('Следующий вопрос'):
            if 'symptoms' not in data:
                data['symptoms'] = None
            await ReportPainCaseForm.was_medecine_taken.set()
            await message.reply(_('Принимались ли пилюли?'),
                                reply_markup=kb.yes_no_kb())
        else:
            if 'symptoms' not in data:
                data['symptoms'] = text
            else:
                data['symptoms'] += f', {text}'
            to_exclude = [el.strip() for el in data['symptoms'].split(',')]
            await ReportPainCaseForm.symptoms.set()
            await message.reply(_('Можно добавить ещё или нажать на "следующий вопрос"'),
                                reply_markup=kb.get_symptoms_kb(exclude=to_exclude))


@dp.message_handler(lambda message: message.text not in [_("Да"), _("Нет")], state=ReportPainCaseForm.was_medecine_taken)
async def process_was_medecine_taken_invalid(message: types.Message):
    return await message.reply(_("Неверный ответ, повторите: "), reply_markup=kb.yes_no_kb())


@dp.message_handler(state=ReportPainCaseForm.was_medecine_taken)
async def process_was_medecine_taken(message: types.Message, state: FSMContext):
    if message.text == _("Нет"):
        await ReportPainCaseForm.description.set()
        await message.reply(_("Примечания, если имеются:"), reply_markup=kb.add_description_kb())
    else:
        reply_markup = await kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)
        reply_markup = reply_markup[0]
        await ReportPainCaseForm.drugname.set()
        await message.reply(_("Название таблетки:"),
                            reply_markup=reply_markup)


@dp.message_handler(lambda message: message.text.strip() == '', state=ReportPainCaseForm.drugname)
async def process_drugname_invalid(message: types.Message):
    reply_markup, __ = await kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)
    return await message.reply(_("Сообщение не может быть пустым, повторите"),
                               reply_markup=reply_markup)


@dp.message_handler(state=ReportPainCaseForm.drugname)
async def process_drugname(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == _('Следующий вопрос'):
            await ReportPainCaseForm.description.set()
            await message.reply(_("Примечания, если имеются:"), reply_markup=kb.add_description_kb())
        else:
            if 'drugname' not in data:
                data['drugname'] = [text]
            else:
                data['drugname'].append(text)
            await ReportPainCaseForm.amount.set()
            await message.reply(_("Количество принятого в мг? (можно написать)"), reply_markup=kb.drug_amount_kb)


@dp.message_handler(state=ReportPainCaseForm.amount)
async def process_amount(message: types.Message, state: FSMContext):
    # Update state and data
    amount = message.text.strip()
    async with state.proxy() as data:
        if 'amount' not in data:
            data['amount'] = [amount]
        else:
            data['amount'].append(amount)
    to_exclude = [el.strip() for el in data['drugname']]
    reply_markup, __ = await kb.get_drugs_kb_and_drugnames(owner=message.from_user.id, exclude=to_exclude, add_next=True)
    await ReportPainCaseForm.drugname.set()
    await message.reply(_('Можно добавить ещё или нажать на "следующий вопрос"'),
                        reply_markup=reply_markup)


@dp.message_handler(state=ReportPainCaseForm.description)
async def process_description(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == _('Не имеются'):
            data['description'] = None
        else:
            data['description'] = text
        data['owner_id'] = message.from_user.id

        await sql.report_paincase(**data)
    text = _("Успешно добавлено!")
    text += _('\nГолова болела <b>{pain_date}</b>\n'
              'В течение <b>{durability} ч.</b>\n'
              'Интенсивность: <b>{intensity}</b>\n'
              '<b>{aura_str}</b>\n'
              'Триггеров: <b>{n_provocateurs}</b>\n'
              'Симптомов: <b>{n_symptoms}</b>\n'
              'Таблетки: <b>{drugs_or_not}</b>\n').format(
        pain_date=data['date'],
        durability=data['durability'],
        intensity=data['intensity'],
        aura_str=_('Аура была') if data['aura'] else _('Ауры не было'),
        n_provocateurs=len(data['provocateurs'].split(',')) if data['provocateurs'] else 0,
        n_symptoms=len(data['symptoms'].split(',')) if data['symptoms'] else 0,
        drugs_or_not=', '.join(data['drugname']) if 'drugname' in data else _('не принимали')
    )
    await bot.send_message(message.chat.id, text, reply_markup=types.ReplyKeyboardRemove())
    # Finish conversation
    await state.finish()
    await remove_user_state(message.from_user.id)
