import logging
from aiogram import executor
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import asyncio
import aioschedule
from src.bot import dp, bot
from src.messages_handler import notif_of_new_users
from src.fsm_forms import *
from db import crud, models
from db.database import engine
from src.routes import regular_report
from src.utils import notify_me
import traceback
from aio_pika import Message, connect
from src.routes import *
import os
import datetime


my_tg_id = int(os.getenv('MY_TG_ID'))


# Schedule notification task
async def notify_users():
    """
    Ask if there was a headache during missing period, defined in notify_every attr
    Notify daily about new users
    """
    all_users: list[models.User] = await crud.get_users()
    deleted_users: list[models.User] = []
    t = datetime.datetime.today()
    time_notified = datetime.datetime.now()
    users_id_w_notif = []
    n_notifyable_users = 0
    # Message to notify me about notification process
    process_message = await bot.send_message(chat_id=my_tg_id, text='Started notification task...')
    for i, user in enumerate(all_users):
        notification_period_days = user.notify_every
        if notification_period_days == -1:   # If user did not specify it yet
            continue
        n_notifyable_users += 1

        notification_period_minutes = notification_period_days * 24 * 60  # Notification period in minutes
        dt = (t - user.last_notified).total_seconds() / 60   # How many minutes since last notification
        if dt >= notification_period_minutes - 65:   # Check if at least 1 day passed (safety interval 65 mins incl.)
            try:
                # Ask user about pains during the day(s)
                await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
                users_id_w_notif.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                if await crud.delete_user(user.telegram_id):
                    deleted_users.append(user)
                else:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        if i % 500 == 0:
            await bot.edit_message_text(chat_id=my_tg_id, message_id=process_message.message_id,
                                        text=f'{i} users processed')
        await asyncio.sleep(0.1)   # As Telegram does not allow more than 30 messages/sec

    # Get notification text about users joined during the day
    text = await notif_of_new_users() + '\n\n'
    text += f'{len(users_id_w_notif)} users notified\n' \
            f'Will change last notified on {time_notified:%d.%m.%Y %H:%M:%S} UTC\n\n'
    await bot.edit_message_text(chat_id=my_tg_id, message_id=process_message.message_id,
                                text=text)

    # Change 'last_notified' for notified users
    await crud.batch_change_last_notified(users_id_w_notif, time_notified)

    # Count users with at least one added row in Pains table - they are active_users
    pains: list[int] = await crud.get_user_ids_pains()
    all_active_users = set(pains)

    # Some statistics from the beginning
    all_users_id = set([user.telegram_id for user in all_users])
    n_active_now = len(all_active_users.intersection(all_users_id))
    n_deleted_after_active = len(all_active_users - all_users_id)

    # Who deleted?
    text_deleted = ''
    for user in deleted_users:
        username = '' if user.user_name is None else 't.me/' + user.user_name
        active = f'active' if user.telegram_id in all_active_users else ''
        if active != '':    # How many rows in db from that user
            n_pains = pains.count(user.telegram_id)
            active += f' ({n_pains} entries)'
        text_deleted += f'{user.first_name} {username} {active} deleted\n'
        await asyncio.sleep(0.001)
    text_deleted += '\n'

    ex_time = (datetime.datetime.now() - time_notified).total_seconds()
    text += f'{n_notifyable_users}/{len(all_users)} users with notification\n' \
            f'{n_active_now} active and {n_deleted_after_active} overall deleted after being active users\n\n' \
            f'{text_deleted}' \
            f'{len(pains)} rows in Pains table\n\n' \
            f'Execution time = {ex_time // 60:.0f} min {ex_time % 60:.0f} sec'
    await bot.edit_message_text(chat_id=my_tg_id, message_id=process_message.message_id,
                                text=text)


async def db_healthcheck():
    if not await crud.healthcheck():
        await notify_me('!Database connection error!')


async def scheduler():
    aioschedule.every().day.at("19:00").do(notify_users)  # UTC tz in docker
    aioschedule.every(10).minutes.do(db_healthcheck)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


async def on_startup(_):
    await bot.set_my_commands([
        types.bot_command.BotCommand('reschedule', 'периодичность опросов'),
        types.bot_command.BotCommand('pain', 'запись бо-бо'),
        types.bot_command.BotCommand('druguse', 'приём лекарства'),
        types.bot_command.BotCommand('check_pains', 'статистика болей'),
        types.bot_command.BotCommand('check_drugs', 'статистика лекарств'),
        types.bot_command.BotCommand('add_drug', 'добавить лекарство'),
    ])
    asyncio.create_task(scheduler())
    await notify_me('Bot restarted')


if __name__ == '__main__':
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s: %(message)s",
            datefmt='%d.%m.%Y %H:%M:%S'
        )
        logging.info('Bot started')
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except:
        asyncio.run(notify_me(traceback.format_exc()))
