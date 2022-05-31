from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage


API_TOKEN = '5494735949:AAF9NFfm2skBPjB_Z7LN8WmHUQsV8ofciXQ'

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
