from aiogram import executor
import aioschedule

from src.routes import *
from db import sql
from db.models import User
from db.redis.models import PydanticUser
from db.redis.crud import init_states
from src.fsm_forms import available_fsm_states
from src.misc.utils import notify_me
from src.misc.db_backup import do_backup
from src.misc.service_reports import everyday_report
from src.misc.init_bot_description import set_bot_name, set_bot_description, set_bot_commands
from src.config import logger
import datetime


# Schedule notification task
async def notify_users_hourly():
    """
    Ask if there was a headache during missing period, defined in notify_every attribute
    """
    utc_hour = datetime.datetime.utcnow().hour
    user_list: list[User] = await sql.users_by_notif_hour(utc_hour)
    if user_list:
        logger.info(f'Notifying {len(user_list)} users')
    t = datetime.datetime.today()
    time_notified = datetime.datetime.now()
    notified_users_ids = []
    # Message to notify me about notification process
    for i, user in enumerate(user_list):
        notification_period_days = user.notify_every
        if notification_period_days == -1:   # If user did not specify it yet
            continue

        notification_period_minutes = notification_period_days * 24 * 60  # Notification period in minutes
        dt = (t - user.last_notified).total_seconds() / 60   # How many minutes since last notification
        if dt >= notification_period_minutes - 65:   # Check if notif. period has passed (safety interval 65 mins incl.)
            try:
                # Ask user about pains during the day(s)
                await regular_report(user_instance=user, missing_days=notification_period_days)
                notified_users_ids.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                result = await sql.delete_user(user.telegram_id)
                if not result:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        await asyncio.sleep(0.1)   # As Telegram does not allow more than 30 messages/sec

    # Change 'last_notified' for notified users
    if notified_users_ids:
        await sql.batch_change_last_notified(notified_users_ids, time_notified)
        logger.info(f'{len(notified_users_ids)} users notified')


async def db_healthcheck():
    if not await sql.healthcheck():
        logger.error(err := '!Database connection error!')
        await notify_me(err)


async def scheduler():
    """
    TZ in docker = UTC
    """
    aioschedule.every().hour.at(":00").do(notify_users_hourly)
    aioschedule.every().day.at("21:30").do(everyday_report)
    aioschedule.every(10).minutes.do(db_healthcheck)
    aioschedule.every().day.at("03:30").do(do_backup)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(10)


async def on_startup(__):
    await init_states(available_fsm_states)
    await set_bot_name()
    await set_bot_description()
    await set_bot_commands()
    asyncio.create_task(scheduler())
    await notify_me('Bot restarted')


if __name__ == '__main__':
    try:
        logger.info('Starting bot...')
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except:
        logger.error(traceback.format_exc())
        asyncio.run(notify_me(traceback.format_exc()))
