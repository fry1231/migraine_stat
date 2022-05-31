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


models.Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=logging.INFO)


# Schedule notification task
async def notify_users():
    users = crud.get_users()
    t = datetime.today()
    for user in users:
        notification_period_days = user.notify_every
        if notification_period_days == -1:  # If user did not specify it yet
            continue
        notification_period_minutes = notification_period_days * 24 * 60
        dt = (t - user.last_notified).seconds / 60
        if dt >= notification_period_minutes - 1:
            pass


async def scheduler():
    aioschedule.every().hour.at(":00").do(notify_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
