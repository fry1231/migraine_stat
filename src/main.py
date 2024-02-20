from aiogram import executor
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import aioschedule

from src.bot import _
from src.routes import *
from db import crud
from db.models import User
from db.redis_models import PydanticUser
from db.redis_crud import update_everyday_report, get_current_report
from src.misc.utils import notify_me
from src.misc.db_backup import do_backup
from src.misc.service_reports import everyday_report
from src.config import logger
import datetime


# Schedule notification task
async def notify_users_hourly():
    """
    Ask if there was a headache during missing period, defined in notify_every attribute
    """
    utc_hour = datetime.datetime.utcnow().hour
    user_list: list[User] = await crud.users_by_notif_hour(utc_hour)
    deleted_users: list[PydanticUser] = []
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
                await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
                notified_users_ids.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                if await crud.delete_user(user.telegram_id):
                    deleted_users.append(PydanticUser(
                        telegram_id=user.telegram_id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_name=user.user_name
                    ))
                else:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        await asyncio.sleep(0.1)   # As Telegram does not allow more than 30 messages/sec

    # Change 'last_notified' for notified users
    if notified_users_ids:
        await crud.batch_change_last_notified(notified_users_ids, time_notified)
        logger.info(f'{len(notified_users_ids)} users notified')


async def db_healthcheck():
    if not await crud.healthcheck():
        logger.error(err := '!Database connection error!')
        await notify_me(err)


async def scheduler():
    aioschedule.every().hour.at(":00").do(notify_users_hourly)
    aioschedule.every().day.at("21:30").do(everyday_report)
    aioschedule.every(10).minutes.do(db_healthcheck)
    aioschedule.every().day.at("03:00").do(do_backup)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(10)


async def on_startup(__):
    for locale in ['en', 'uk', 'fr', 'es', 'ru']:
        language_code = None if locale == 'ru' else locale
        await bot.set_my_commands([
            types.bot_command.BotCommand('pain', _('запись бо-бо', locale=locale)),
            types.bot_command.BotCommand('druguse', _('приём лекарства', locale=locale)),
            types.bot_command.BotCommand('pressure', _('запись давления', locale=locale)),
            types.bot_command.BotCommand('medications', _('список лекарств', locale=locale)),
            types.bot_command.BotCommand('calendar', _('изменить записи', locale=locale)),
            types.bot_command.BotCommand('statistics', _('статистика', locale=locale)),
            types.bot_command.BotCommand('settings', _('настройки', locale=locale)),
        ], language_code=language_code)

    asyncio.create_task(scheduler())
    await notify_me('Bot restarted')
    logger.info('Bot started')


if __name__ == '__main__':
    try:
        logger.info('Starting bot...')
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except:
        asyncio.run(notify_me(traceback.format_exc()))
        logger.error(traceback.format_exc())
