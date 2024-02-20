from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from src.config import API_TOKEN, IS_TESTING, logger, LOCALES_DIR
from src.middlewares import CustomI18nMiddleware


# Initialize bot and dispatcher
validate = False if IS_TESTING else True
bot = Bot(token=API_TOKEN, validate_token=validate, parse_mode=types.ParseMode.HTML)
storage = RedisStorage2('redis', 6379, db=0, pool_size=10, prefix='fsm')
dp = Dispatcher(bot, storage=storage)

I18N_DOMAIN = 'messages'

# Setup i18n middleware
i18n = CustomI18nMiddleware(I18N_DOMAIN, LOCALES_DIR)
dp.middleware.setup(i18n)
_ = i18n.gettext
