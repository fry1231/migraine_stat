import os
import logging
import aioredis
import asyncio
from pathlib import Path
from alembic.config import Config


SRC_DIR = Path(__file__).parent
BASE_DIR = SRC_DIR.parent
LOCALES_DIR = SRC_DIR / 'locales'
PERSISTENT_DATA_DIR = Path('/usr/persistent_data/')

# Alembic
alembic_cfg = Config(str(BASE_DIR / 'alembic.ini'))

# Get env vars
IS_TESTING = True if os.getenv('IS_TESTING', default='0') == '1' else False
API_TOKEN = os.getenv('API_TOKEN')
IN_PRODUCTION = True if os.getenv('IN_PRODUCTION') == '1' else False
MY_TG_ID = os.getenv('MY_TG_ID')
if MY_TG_ID is not None and MY_TG_ID != '':
    MY_TG_ID = int(MY_TG_ID)
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASS = os.getenv('POSTGRES_PASS')
PAYMENTS_TOKEN_RU = os.getenv('PAYMENTS_TOKEN_RU')

# Setting up Redis connection
if IS_TESTING:
    db_num = 5
else:
    db_num = 1
redis_conn: aioredis.Redis = asyncio.get_event_loop().run_until_complete(
    aioredis.from_url("redis://redis", db=db_num, decode_responses=True))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)s)',
    datefmt='%d.%m.%Y_%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler('/path/to/your/logfile.log'),
    ]
)
logger = logging.getLogger(__name__)

if IN_PRODUCTION:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.DEBUG)


# @asynccontextmanager
# async def rabbit_channel() -> AbstractChannel:
#     """
#     Establishes a connection to the RabbitMQ server using
#         the credentials provided as environment variables.
#     Creates a channel within the connection
#
#     Yields a channel (durable)
#     Notifies and raises on error
#     """
#     user = getenv('RABBITMQ_USER')
#     passw = getenv('RABBITMQ_PASS')
#     host = getenv('RABBITMQ_HOST')
#     connection = await connect_robust(f"amqp://{user}:{passw}@{host}/")
#     try:
#         async with connection:
#             channel = await connection.channel()
#             yield channel
#     except Exception:
#         logger.error('Error while dealing with RabbitMQ:\n' + traceback.format_exc())
#     finally:
#         await connection.close()
