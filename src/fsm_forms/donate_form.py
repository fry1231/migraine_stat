from aiogram import types
from aiogram.types.message import ContentTypes
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from db import crud
from src.bot import dp, bot
from src.fsm_forms import keyboards as kb
from db import crud
from src.misc.utils import notify_me
from src.config import PAYMENTS_TOKEN_RU


class Donation(StatesGroup):
    amount = State()


async def get_user_desc(message: types.Message):
    user_id = message.from_user.id
    user = await crud.get_user(telegram_id=user_id)
    username = ''
    if user.user_name is not None:
        username = ' t.me/' + user.user_name
    return f'{user.telegram_id} {user.first_name}{username} '


@dp.message_handler(commands=['donate'], state='*')
async def donate_entry(message: types.Message, state: FSMContext = None):
    """Conversation entrypoint"""
    if state and await state.get_state():
        await state.finish()
    # Set state
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} entered DonateForm')
    await Donation.amount.set()
    await message.reply("Спасибо, что хотите меня поддержать!\n"
                        "Напишите, пожалуйста, на какую сумму?\n"
                        "Можно выбрать или написать вручную\n"
                        "(Минимум для платёжной системы - 60 рублей)",
                        reply_markup=kb.donate_amount_kb)


# Check donate amount. Should be digit
@dp.message_handler(lambda message: not message.text.strip().replace(',', '.').isdigit(), state=Donation.amount)
async def check_amount(message: types.Message):
    return await message.reply("В сообщении должно быть число:", reply_markup=kb.donate_amount_kb)


@dp.message_handler(lambda message: message.text.strip().replace(',', '.').isdigit() and
                                    float(message.text.strip().replace(',', '.')) < 60, state=Donation.amount)
async def check_amount2(message: types.Message):
    return await message.reply("К сожалению, платёжная система не даёт выставлять счета меньше 60 рублей :(",
                               reply_markup=kb.donate_amount_kb)


@dp.message_handler(state=Donation.amount)
async def donate_amount(message: types.Message, state: FSMContext):
    amount = round(float(message.text.strip().replace(',', '.')), 2)
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} donate amount {amount}')
    await bot.send_invoice(message.chat.id,
                           title='Жертва богу головной боли',
                           description='Пойдёт на оплату хостинга, ибупрофена и корма для кошки (на картинке)',
                           provider_token=PAYMENTS_TOKEN_RU,
                           currency='rub',
                           photo_url='https://telegra.ph/file/c6460e669b3f9067966b2.jpg',
                           photo_height=512,
                           photo_width=512,
                           prices=[types.LabeledPrice(label='Donate', amount=int(amount*100))],
                           payload=f'{user_desc}%{amount}')
    await state.finish()


@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=ContentTypes.SUCCESSFUL_PAYMENT)
async def got_payment(message: types.Message):
    user_desc = await get_user_desc(message)
    await notify_me(f'{user_desc} donated')
    await bot.send_message(message.chat.id,
                           'Ура, спасибо!',
                           reply_markup=types.ReplyKeyboardRemove())
