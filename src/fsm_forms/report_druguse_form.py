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


class ReportDrugUseForm(StatesGroup):
    datetime = State()
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
#     if text not in valid_drugnames:
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


@dp.message_handler(commands=['druguse'])
async def add_drug_entry(message: types.Message):
    """Conversation entrypoint"""
    # Set state
    await ReportDrugUseForm.datetime.set()
    await message.reply("Дата приёма (в формате dd.mm.yyyy):", reply_markup=kb.get_date_kb())


@dp.message_handler(lambda message: not is_date_valid(message.text), state=ReportDrugUseForm.datetime)
async def process_datetime_invalid(message: types.Message):
    """
    If datetime is invalid
    """
    return await message.reply("Неверный формат даты. Попробуй ещё раз.", reply_markup=kb.get_date_kb())


@dp.message_handler(state=ReportDrugUseForm.datetime)
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
    await ReportDrugUseForm.next()
    await message.reply("Что принимали?", reply_markup=kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)[0])


@dp.message_handler(lambda message: message.text.strip() == '', state=ReportDrugUseForm.drugname)
async def process_drugname_invalid(message: types.Message):
    return await message.reply("Сообщение не может быть пустым, повторите",
                               reply_markup=kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)[0])


@dp.message_handler(state=ReportDrugUseForm.drugname)
async def process_drugname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['drugname'] = message.text.strip()
    await ReportDrugUseForm.next()
    await message.reply("Количество принятого?", reply_markup=kb.drug_amount_kb)


# Check daily_max. Gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=ReportDrugUseForm.amount)
async def process_amount_invalid(message: types.Message):
    """
    If amount is invalid
    """
    return await message.reply("Количество должно быть числом, повторите ввод:", reply_markup=kb.drug_amount_kb)


@dp.message_handler(lambda message: message.text.isdigit(), state=ReportDrugUseForm.amount)
async def process_amount(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['amount'] = int(message.text.strip())
    crud.report_druguse(when=data['datetime'],
                        amount=data['amount'],
                        who=message.from_user.id,
                        drugname=data['drugname'],
                        # paincase_id=
                        )
    await bot.send_message(message.chat.id, "Успешно добавлено!", reply_markup=types.ReplyKeyboardRemove())
    # Finish conversation
    await state.finish()
