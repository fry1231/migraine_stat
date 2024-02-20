from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import asyncio

from src.config import IN_PRODUCTION, POSTGRES_USER, POSTGRES_PASS, logger


SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASS}@migraine_db:5432/db_prod"
TEST_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASS}@migraine_db:5432/db_test"


engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=not IN_PRODUCTION
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
)


async def database_exists(url):
    async with engine.begin() as conn:
        result = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{url.database}'"))
        result = result.fetchone()
        return bool(result)


async def create_database(url):
    async with engine.begin() as conn:
        await conn.execute(text("COMMIT"))
        await conn.execute(text(f"CREATE DATABASE {url.database}"))


async def check_db():
    if not await database_exists(engine.url):
        await create_database(engine.url)
        logger.info(f"DB {SQLALCHEMY_DATABASE_URL} created")
    else:
        logger.info(f"Database already exists")

loop = asyncio.get_event_loop()
loop.run_until_complete(check_db())
