import logging
from aiogram import executor
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
import asyncio
import aioschedule
from src.bot import dp, bot
from src.routes import *
from src.fsm_forms import *
from db import crud, models
from db.database import engine
from src.utils import notify_me, notify_users
import traceback
from aio_pika import Message, connect


# Configure logging
logging.basicConfig(level=logging.INFO)


async def scheduler():
    aioschedule.every().day.at("21:00").do(notify_users)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


async def on_startup(_):
    await bot.set_my_commands([
        types.bot_command.BotCommand('reschedule', 'периодичность опросов'),
        types.bot_command.BotCommand('pain', 'запись бо-бо'),
        types.bot_command.BotCommand('druguse', 'запись использования лекарства'),
        types.bot_command.BotCommand('check_drugs', 'статистика употребления лекарств'),
        types.bot_command.BotCommand('check_pains', 'статистика болей'),
        types.bot_command.BotCommand('add_drug', 'добавить используемое лекарство'),
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
