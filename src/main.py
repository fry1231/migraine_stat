import logging
from aiogram import executor
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import asyncio
import aioschedule
from src.bot import dp, bot
from src.routes import *
from src.fsm_forms import *
from db import crud, models
from datetime import datetime
from db.database import SessionLocal, engine
from src.utils import notify_me
import traceback


models.Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=logging.INFO)


# Schedule notification task
async def notify_users():
    """
    Ask if there was a headache during missing period, defined in notify_every attr
    """
    users = crud.get_users()
    t = datetime.today()
    time_notified = datetime.now()
    users_arr = []
    for user in users:
        notification_period_days = user.notify_every
        if notification_period_days == -1:  # If user did not specify it yet
            continue
        notification_period_minutes = notification_period_days * 24 * 60
        dt = (t - user.last_notified).total_seconds() / 60
        if dt >= notification_period_minutes - 5:
            try:
                await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
                await notify_me(f'User {user.telegram_id} notified')
                users_arr.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                if crud.delete_user(user.telegram_id):
                    await notify_me(f'User {user.telegram_id} ({user.user_name} / {user.first_name}) deleted')
                else:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        for user_id in users_arr:
            crud.change_last_notified(user_id, time_notified)
        await notify_me(f'Changed last notified for users on {time_notified}')


async def scheduler():
    aioschedule.every().day.at("21:00").do(notify_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


async def on_startup(_):
    await notify_me('Bot restarted')
    await bot.set_my_commands([
        types.bot_command.BotCommand('reschedule', 'периодичность опросов'),
        types.bot_command.BotCommand('pain', 'запись бо-бо'),
        types.bot_command.BotCommand('druguse', 'запись использования лекарства'),
        types.bot_command.BotCommand('check_drugs', 'статистика употребления лекарств'),
        types.bot_command.BotCommand('check_pains', 'статистика болей'),
        types.bot_command.BotCommand('add_drug', 'добавить используемое лекарство'),
    ])
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    try:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except:
        asyncio.run(notify_me(traceback.format_exc()))
