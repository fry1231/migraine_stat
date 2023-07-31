from aiogram import Bot, Dispatcher, types
import aiogram.utils.markdown as md
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from src.bot import dp, bot
from src.fsm_forms import keyboards as kb
from db import crud


class AddDrugForm(StatesGroup):
    name = State()
    daily_max = State()
    is_painkiller = State()
    is_temp_reducer = State()


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


@dp.message_handler(commands=['add_drug'])
async def add_drug_entry(message: types.Message):
    """Conversation entrypoint"""
    # Set state
    await AddDrugForm.name.set()
    await message.reply("Введите название:")


@dp.message_handler(state=AddDrugForm.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Process drug name
    """
    async with state.proxy() as data:
        data['name'] = message.text.strip()
    await AddDrugForm.next()
    await message.reply("Какова максимальная суточная доза (в мг)? - "
                        "выберите из предложенных или напишите свой вариант",
                        reply_markup=kb.drug_amount_kb)


# Check daily_max. Gotta be digit
@dp.message_handler(lambda message: not message.text.isdigit(), state=AddDrugForm.daily_max)
async def process_daily_max_invalid(message: types.Message):
    """
    If daily_max is invalid
    """
    return await message.reply("Количество должно быть числом, повторите ввод:", reply_markup=kb.drug_amount_kb)


@dp.message_handler(lambda message: message.text.isdigit(), state=AddDrugForm.daily_max)
async def process_daily_max(message: types.Message, state: FSMContext):
    # Update state and data
    await AddDrugForm.next()
    await state.update_data(daily_max=int(message.text.strip()))

    await message.reply("Является обезболивающим?", reply_markup=kb.yes_no_kb)


@dp.message_handler(lambda message: message.text not in ["Да", "Нет"], state=AddDrugForm.is_painkiller)
async def process_is_painkiller_invalid(message: types.Message):
    return await message.reply("Неверный ответ, повторите: ", reply_markup=kb.yes_no_kb)


@dp.message_handler(state=AddDrugForm.is_painkiller)
async def process_is_painkiller(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['is_painkiller'] = True if message.text == "Да" else False
    await AddDrugForm.next()
    await message.reply("Является жаропонижающим?",
                        reply_markup=kb.yes_no_kb)


@dp.message_handler(lambda message: message.text not in ["Да", "Нет"], state=AddDrugForm.is_temp_reducer)
async def process_is_temp_reducer_invalid(message: types.Message):
    return await message.reply("Неверный ответ, повторите: ", reply_markup=kb.yes_no_kb)


@dp.message_handler(state=AddDrugForm.is_temp_reducer)
async def process_is_temp_reducer(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['is_temp_reducer'] = True if message.text == "Да" else False

    await crud.add_drug(
        name=data['name'],
        daily_max=data['daily_max'],
        is_painkiller=data['is_painkiller'],
        is_temp_reducer=data['is_temp_reducer'],
        user_id=message.from_user.id
    )
    await bot.send_message(
                message.chat.id,
                md.text(
                    md.text('Добавлен ', md.bold(data['name'])),
                    md.text('Дозировка макс.: ', md.bold(data['daily_max'])),
                    md.text('Обезболивающее: ', md.bold(data['is_painkiller'])),
                    md.text('Жаропонижающее: ', md.bold(data['is_temp_reducer'])),
                    sep='\n',
                ),
                reply_markup=types.ReplyKeyboardRemove(),
                parse_mode=ParseMode.MARKDOWN,
            )
    # Finish conversation
    await state.finish()
