import logging
from aiogram import executor
import asyncio
import aioschedule
from src.bot import dp, bot
from src.routes import *
from src.fsm_forms import *
from db import crud, models
from datetime import datetime
from db.database import SessionLocal, engine
from src.utils import notify_me


models.Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=logging.INFO)


# Schedule notification task
def notify_users():
    """
    Ask if there was a headache during missing period, defined in notify_every attr
    """
    users = crud.get_users()
    t = datetime.today()
    for user in users:
        notification_period_days = user.notify_every
        if notification_period_days == -1:  # If user did not specify it yet
            continue
        notification_period_minutes = notification_period_days * 24 * 60
        dt = (t - user.last_notified).total_seconds() / 60
        if dt >= notification_period_minutes - 1:
            await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
            await notify_me(f'User {user.telegram_id} notified')


async def scheduler():
    aioschedule.every().hour.at(":00").do(notify_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


async def on_startup(_):
    await bot.set_my_commands([
        types.bot_command.BotCommand('reschedule', 'настроить периодичность опросов'),
        types.bot_command.BotCommand('pain', 'сделать запись бо-бо'),
        types.bot_command.BotCommand('druguse', 'сделать запись использования лекарства'),
        types.bot_command.BotCommand('check_drugs', 'узнать статистику употребления лекарств'),
        types.bot_command.BotCommand('check_pains', 'узнать статистику болей'),
        types.bot_command.BotCommand('add_drug', 'добавить используемое лекарство'),
    ])
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
