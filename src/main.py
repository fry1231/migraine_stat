import logging
from datetime import datetime
from typing import List

from aiogram import executor
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import asyncio
import aioschedule
from src.bot import dp, bot
from src.messages_handler import notif_of_new_users
from src.routes import *
from src.fsm_forms import *
from db import crud, models
from db.database import engine
from src.routes import regular_report
from src.utils import notify_me
import traceback
from aio_pika import Message, connect


# Configure logging
logging.basicConfig(level=logging.INFO)


# Schedule notification task
async def notify_users():
    """
    Ask if there was a headache during missing period, defined in notify_every attr
    Notify daily about new users
    """
    users: List[models.User] = await crud.get_users()
    t = datetime.today()
    time_notified = datetime.now()
    users_id_w_notif = []
    n_notifyable_users = 0
    for user in users:
        notification_period_days = user.notify_every
        if notification_period_days == -1:  # If user did not specify it yet
            continue
        n_notifyable_users += 1
        notification_period_minutes = notification_period_days * 24 * 60
        dt = (t - user.last_notified).total_seconds() / 60
        if dt >= notification_period_minutes - 15:
            try:
                await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
                users_id_w_notif.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                if await crud.delete_user(user.telegram_id):
                    await notify_me(f'User {user.telegram_id} ({user.user_name} / {user.first_name}) deleted')
                else:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        await asyncio.sleep(1/30)   # As Telegram does not allow more than 30 messages/sec
    new_users_text = await notif_of_new_users()
    await notify_me(new_users_text)
    await notify_me(
        f'{len(users_id_w_notif)} users notified\n'
        f'Will change last notified on {time_notified}'
    )

    try:
        await crud.batch_change_last_notified(users_id_w_notif)
    except Exception:
        await notify_me('Error while executing batch_change_last_notified, fallback to the old version')
        await notify_me(traceback.format_exc())
        for user_id in users_id_w_notif:
            await crud.change_last_notified(user_id, time_notified)

    # Count users with at least one added row in Pains table
    active_users = set()
    pains: List[models.PainCase] = await crud.get_pains()
    for pain in pains:
        active_users.add(pain.owner_id)

    n_active = len(active_users.intersection(users_id_w_notif))
    n_deleted = len(active_users - set(users_id_w_notif))

    ex_time = (datetime.now() - time_notified).total_seconds()
    await notify_me(
        f'{n_notifyable_users}/{len(users)} users with notification\n'
        f'{n_active} active and {n_deleted} deleted after being active users\n'
        f'{len(pains)} rows in Pains table\n\n'
        f'Execution time = {ex_time // 60} min {ex_time % 60} sec'
    )


async def scheduler():
    aioschedule.every().day.at("21:00").do(notify_users)
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
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except:
        asyncio.run(notify_me(traceback.format_exc()))
