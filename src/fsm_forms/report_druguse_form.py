from aiogram import Bot, Dispatcher, types
import aiogram.utils.markdown as md
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode

from db import crud
from src.bot import dp, bot, _
from src.fsm_forms import keyboards as kb
from db import crud
from datetime import date, datetime, timedelta
import pytz


class ReportDrugUseForm(StatesGroup):
    date = State()
    drugname = State()
    amount = State()
    # owner_id
    # paincase_id


@dp.message_handler(commands=['druguse'], state='*')
async def du_add_drug_entry(message: types.Message, state: FSMContext = None):
    """Conversation entrypoint"""
    if state and await state.get_state():
        await state.finish()
    user_id = message.from_user.id
    user = await crud.get_user(telegram_id=user_id)
    tz = user.timezone
    date_today = datetime.now(pytz.timezone(tz)).date()
    await ReportDrugUseForm.date.set()
    # NOTE Date of a medication intake
    await message.reply(_("Дата приёма?"), reply_markup=kb.get_date_kb(date_today, 'druguse'))


@dp.callback_query_handler(lambda c: c.data, state=ReportDrugUseForm.date)
async def du_process_datetime(callback_query: types.CallbackQuery, state: FSMContext):
    ddate = callback_query.data.split('_')[-1]
    async with state.proxy() as data:
        data['date'] = ddate
    reply_markup, __ = await kb.get_drugs_kb_and_drugnames(owner=callback_query.from_user.id)
    await ReportDrugUseForm.next()
    text = f'<b>{ddate}</b>\n' + _("Что принимали? (можно написать)")
    await bot.send_message(callback_query.from_user.id, text, reply_markup=reply_markup)
    await callback_query.message.delete()


@dp.message_handler(lambda message: message.text.strip() == '', state=ReportDrugUseForm.drugname)
async def du_process_drugname_invalid(message: types.Message):
    reply_markup, __ = await kb.get_drugs_kb_and_drugnames(owner=message.from_user.id)
    return await message.reply(_("Сообщение не может быть пустым, повторите"),
                               reply_markup=reply_markup)


@dp.message_handler(state=ReportDrugUseForm.drugname)
async def du_process_drugname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['drugname'] = message.text.strip()
    await ReportDrugUseForm.next()
    await message.reply(_("Количество принятого? (можно написать)"), reply_markup=kb.drug_amount_kb)


@dp.message_handler(state=ReportDrugUseForm.amount)
async def du_process_amount(message: types.Message, state: FSMContext):
    # Update state and data
    async with state.proxy() as data:
        data['amount'] = message.text.strip()
    await crud.report_druguse(date=data['date'],
                                          amount=data['amount'],
                                          owner_id=message.from_user.id,
                                          drugname=data['drugname'])
    text = _("Успешно добавлено!")
    text += f"\n\n{data['date']} {data['drugname']} {data['amount']}"
    await bot.send_message(message.chat.id, text, reply_markup=types.ReplyKeyboardRemove())
    # Finish conversation
    await state.finish()
