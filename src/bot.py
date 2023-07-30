from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from src.settings import API_TOKEN, IS_TESTING


# Initialize bot and dispatcher
validate = False if IS_TESTING else True
bot = Bot(token=API_TOKEN, validate_token=validate)
dp = Dispatcher(bot, storage=MemoryStorage())
