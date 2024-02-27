import aiogram
from src.routes.common import *    # always import first
from src.routes.admin_commands import *
from src.routes.drugs_management import *
from src.routes.settings import *
from src.routes.statistics import *
from src.routes.user_interactions import *

from src.routes.calendar import *
from src.fsm_forms import *
from src.config import MY_TG_ID


@dp.message_handler(state='*')
async def handle_other(message: types.Message, state: FSMContext):
    """
    Handle messages depending on its context
    """
    # If I want to reply to someone
    if message.from_user.id == MY_TG_ID:
        if message.reply_to_message is not None:
            message_with_credentials: types.Message = message.reply_to_message
            splitted = message_with_credentials.text.split('\n')
            user_id_row = [el for el in splitted if el.startswith('user_id=')][-1]
            user_id = int(user_id_row.replace('user_id=', ''))

            message_id_row = [el for el in splitted if el.startswith('message_id=')][-1]
            reply_message_id = int(message_id_row.replace('message_id=', ''))

            text_to_reply = message.text

            await bot.send_message(chat_id=user_id,
                                   text=text_to_reply,
                                   reply_to_message_id=reply_message_id)
            await notify_me('Message sent')
    else:
        try:
            text = f'User {message.from_user.username} / {message.from_user.first_name} ' \
                   f'user_id={message.from_user.id}\n' \
                   f'message_id={message.message_id}'
            await bot.send_message(chat_id=MY_TG_ID,
                                   text=text,
                                   reply_to_message_id=message.message_id)
            await message.forward(MY_TG_ID)
        except (aiogram.utils.exceptions.TelegramAPIError, aiogram.utils.exceptions.BadRequest):
            await notify_me(f'User {message.from_user.username} / {message.from_user.first_name} '
                            f'writes:\n{message.text}\n\n'
                            f'user_id={message.from_user.id}\n'
                            f'message_id={message.message_id}')
