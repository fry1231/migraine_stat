from aiogram import Bot, Dispatcher, types
import aiogram.utils.markdown as md
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from src.bot import dp, bot
from src.fsm_forms import keyboards as kb
from db import crud
from datetime import date, datetime, timedelta


class ReportPainCaseForm(StatesGroup):
    datetime = State()
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


def is_date_valid(text):
    text = text.strip()
    if text not in ['Сегодня', 'Вчера', 'Позавчера']:
        try:
            datetime.strptime(text, '%d.%m.%Y')
        except ValueError:
            return False
    return True


# def is_drugname_valid(text):
#     text = text.strip()
#     _, valid_drugnames = kb.get_drugs_kb_and_drugnames()
#     if text not in valid_drugnames and text != 'Следующий вопрос':
#         return False
#     return True


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    # Cancel state and inform user about it
    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['pain'])
async def add_paincase_entry(message: types.Message):
    """Conversation entrypoint"""
    # Set state
    await ReportPainCaseForm.datetime.set()
    await message.reply("Когда? (в формате dd.mm.yyyy)", reply_markup=kb.get_date_kb())


@dp.message_handler(lambda message: not is_date_valid(message.text), state=ReportPainCaseForm.datetime)
async def process_datetime_invalid(message: types.Message):
    """
    If datetime is invalid
    """
    return await message.reply("Неверный формат даты. Попробуй ещё раз.", reply_markup=kb.get_date_kb())


@dp.message_handler(state=ReportPainCaseForm.datetime)
async def process_datetime(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        text = message.text.strip()
        assoc_dict = {
            'Сегодня': date.today(),
            'Вчера': date.today() - timedelta(days=1),
            'Позавчера': date.today() - timedelta(days=2),
        }
        if text in ['Сегодня', 'Вчера', 'Позавчера']:
            data['datetime'] = assoc_dict[text]
        else:
            data['datetime'] = datetime.strptime(text, '%d.%m.%Y')
    await ReportPainCaseForm.durability.set()
    await message.reply("Продолжительность в часах (можно написать):", reply_markup=kb.durability_hours_kb)


@dp.message_handler(lambda message: not message.text.isdigit(), state=ReportPainCaseForm.durability)
async def process_durability_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply("Продолжительность должна быть числом, повторите ввод:", reply_markup=kb.durability_hours_kb)


@dp.message_handler(lambda message: message.text.isdigit(), state=ReportPainCaseForm.durability)
async def process_durability(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['durability'] = int(message.text.strip())
    await ReportPainCaseForm.intensity.set()
    await message.reply("Интенсивность от 1 до 10:", reply_markup=kb.durability_hours_kb)


@dp.message_handler(lambda message: not message.text.isdigit(), state=ReportPainCaseForm.intensity)
async def process_intensity_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply("Интенсивность должна быть числом, повторите ввод:", reply_markup=kb.durability_hours_kb)


@dp.message_handler(lambda message: message.text.isdigit(), state=ReportPainCaseForm.intensity)
async def process_intensity(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['intensity'] = int(message.text.strip())
    await ReportPainCaseForm.aura.set()
    await message.reply("Была ли аура?", reply_markup=kb.yes_no_kb)


@dp.message_handler(lambda message: message.text not in ["Да", "Нет"], state=ReportPainCaseForm.aura)
async def process_aura_invalid(message: types.Message):
    return await message.reply("Неверный ответ, повторите: ", reply_markup=kb.yes_no_kb)


@dp.message_handler(state=ReportPainCaseForm.aura)
async def process_aura(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['aura'] = True if message.text == "Да" else False
    await ReportPainCaseForm.provocateurs.set()
    await message.reply("Выбери триггеры при наличии:", reply_markup=kb.get_provocateurs_kb())


@dp.message_handler(state=ReportPainCaseForm.provocateurs)
async def process_provocateurs(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == 'Следующий вопрос':
            if 'provocateurs' not in data:
                data['provocateurs'] = None
            await ReportPainCaseForm.symptoms.set()
            await message.reply('Были ли следующие симптомы?',
                                reply_markup=kb.get_symptoms_kb())
        else:
            if 'provocateurs' not in data:
                data['provocateurs'] = text
            else:
                data['provocateurs'] += f', {text}'
            to_exclude = [el.strip() for el in data['provocateurs'].split(',')]
            await ReportPainCaseForm.provocateurs.set()
            await message.reply('Можно добавить ещё или нажать на "следующий вопрос"',
                                reply_markup=kb.get_provocateurs_kb(exclude=to_exclude))


@dp.message_handler(state=ReportPainCaseForm.symptoms)
async def process_symptoms(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == 'Следующий вопрос':
            if 'symptoms' not in data:
                data['symptoms'] = None
            await ReportPainCaseForm.was_medecine_taken.set()
            await message.reply('Принимались ли пилюли?',
                                reply_markup=kb.yes_no_kb)
        else:
            if 'symptoms' not in data:
                data['symptoms'] = text
            else:
                data['symptoms'] += f', {text}'
            to_exclude = [el.strip() for el in data['symptoms'].split(',')]
            await ReportPainCaseForm.symptoms.set()
            await message.reply('Можно добавить ещё или нажать на "Следующий вопрос"',
                                reply_markup=kb.get_symptoms_kb(exclude=to_exclude))


@dp.message_handler(lambda message: message.text not in ["Да", "Нет"], state=ReportPainCaseForm.was_medecine_taken)
async def process_was_medecine_taken_invalid(message: types.Message):
    return await message.reply("Неверный ответ, повторите: ", reply_markup=kb.yes_no_kb)


@dp.message_handler(state=ReportPainCaseForm.was_medecine_taken)
async def process_was_medecine_taken(message: types.Message, state: FSMContext):
    if message.text == "Нет":
        await ReportPainCaseForm.description.set()
        await message.reply("Примечания, если имеются:", reply_markup=kb.add_description_kb)
    else:
        await ReportPainCaseForm.drugname.set()
        await message.reply("Название таблетки:",
                            reply_markup=kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)[0])


@dp.message_handler(lambda message: message.text.strip() == '', state=ReportPainCaseForm.drugname)
async def process_drugname_invalid(message: types.Message):
    return await message.reply("Сообщение не может быть пустым, повторите",
                               reply_markup=kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)[0])


@dp.message_handler(state=ReportPainCaseForm.drugname)
async def process_drugname(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == 'Следующий вопрос':
            await ReportPainCaseForm.description.set()
            await message.reply("Примечания, если имеются:", reply_markup=kb.add_description_kb)
        else:
            if 'drugname' not in data:
                data['drugname'] = message.text.strip()
            else:
                data['drugname'] += f', {text}'
            await ReportPainCaseForm.amount.set()
            await message.reply("Количество принятого в мг? (можно написать)", reply_markup=kb.drug_amount_kb)


@dp.message_handler(lambda message: not message.text.isdigit(), state=ReportPainCaseForm.amount)
async def process_amount_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply("Количество должно быть числом, повторите ввод:", reply_markup=kb.drug_amount_kb)


@dp.message_handler(lambda message: message.text.isdigit(), state=ReportPainCaseForm.amount)
async def process_amount(message: types.Message, state: FSMContext):
    # Update state and data
    amount = int(message.text.strip())
    async with state.proxy() as data:
        if 'amount' not in data:
            data['amount'] = str(amount)
        else:
            data['amount'] += f', {amount}'
    to_exclude = [el.strip() for el in data['drugname'].split(',')]
    await ReportPainCaseForm.drugname.set()
    await message.reply('Можно добавить ещё или нажать на "Следующий вопрос"',
                        reply_markup=kb.get_drugs_kb_and_drugnames(owner=message.from_user.id, exclude=to_exclude, add_next=True)[0])


@dp.message_handler(state=ReportPainCaseForm.description)
async def process_description(message: types.Message, state: FSMContext):
    text = message.text.strip()
    async with state.proxy() as data:
        if text == 'Не имеются':
            data['description'] = None
        else:
            data['description'] = text
        data['who'] = message.from_user.id
        data['when'] = data['datetime']

        if 'drugname' not in data:
            data['drugname'] = None
            data['amount'] = None

        crud.report_paincase(**data)

    await bot.send_message(message.chat.id, "Успешно добавлено!", reply_markup=types.ReplyKeyboardRemove())
    # Finish conversation
    await state.finish()
