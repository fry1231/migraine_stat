from aiogram import Bot, Dispatcher, types
from aiogram.types.message import ContentTypes
import aiogram.utils.markdown as md
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from src.bot import dp, bot
from src.fsm_forms import keyboards as kb
from db import crud
from src.utils import notify_me
import os


class Donation(StatesGroup):
    amount = State()


async def get_user_desc(message: types.Message):
    user_id = message.from_user.id
    user = await crud.get_user(telegram_id=user_id)
    username = ''
    if user.user_name is not None:
        username = ' t.me/' + user.user_name
    return f'{user.telegram_id} {user.first_name}{username} '


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


@dp.message_handler(commands=['donate'])
async def donate_entry(message: types.Message):
    """Conversation entrypoint"""
    # Set state
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} entered DonateForm')
    await Donation.amount.set()
    await message.reply("Спасибо, что хотите меня поддержать!\n"
                        "Напишите, пожалуйста, на какую сумму?\n"
                        "(можно выбрать или написать вручную)",
                        reply_markup=kb.donate_amount_kb)


# Check donate amount. Should be digit
@dp.message_handler(lambda message: not message.text.strip().replace(',', '.').isdigit(), state=Donation.amount)
async def check_amount(message: types.Message):
    return await message.reply("В сообщении должно быть число:", reply_markup=kb.donate_amount_kb)


@dp.message_handler(state=Donation.amount)
async def donate_amount(message: types.Message, state: FSMContext):
    amount = round(float(message.text.strip().replace(',', '.')), 2)
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} donate amount {amount}')
    await bot.send_invoice(message.chat.id,
                           # title='Жертва богу головной боли',
                           title='Поддержка',
                           # description='Пойдёт на оплату хостинга, ибупрофена и корма для кошки (на картинке)',
                           description='Пойдёт на оплату хостинга и ибупрофена',
                           provider_token=os.getenv('PAYMENTS_TOKEN_RU'),
                           currency='rub',
                           photo_url='https://telegra.ph/file/c6460e669b3f9067966b2.jpg',
                           photo_height=512,
                           photo_width=512,
                           prices=[types.LabeledPrice(label='Donate', amount=int(amount*100))],
                           payload=f'{user_desc}%{amount}')
    await state.finish()


@dp.pre_checkout_query_handler(func=lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=ContentTypes.SUCCESSFUL_PAYMENT)
async def got_payment(message: types.Message):
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} donated!')
    await bot.send_message(message.chat.id,
                           'Ура, спасибо!')
