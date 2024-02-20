import traceback
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy import text as raw_query
from sqlalchemy.ext.asyncio import async_sessionmaker, async_scoped_session
import asyncio

from db.models import PainCase, DrugUse, Drug, Pressure
from db.database import engine, test_engine
from src.config import logger

from src.config import IS_TESTING

if IS_TESTING:
    use_engine = test_engine
else:
    use_engine = engine

async_session_factory = async_sessionmaker(
    use_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=True,
)


# def to_async(func):
#     @wraps(func)
#     async def wrapper(*args, **kwargs):
#         return await asyncio.to_thread(func, *args, **kwargs)
#     return wrapper


@asynccontextmanager
async def get_session() -> async_scoped_session:
    session = async_scoped_session(session_factory=async_session_factory, scopefunc=asyncio.current_task)
    try:
        yield session()
    except Exception:
        await session.rollback()
        logger.error(f'Error while CRUD: {traceback.format_exc()}')
    else:
        try:
            await session.commit()
        except Exception:
            logger.error(f'Error while commiting transaction: {traceback.format_exc()}')
            await session.rollback()
    finally:
        await session.close()


async def healthcheck():
    async with get_session() as session:
        try:
            result = await session.execute(raw_query('SELECT 1'))
            result = result.fetchone()
            return bool(result)
        except Exception:
            return False


async def get_item_by_id(item_type: str, item_id: int) -> PainCase | DrugUse | Pressure | Drug:
    async with get_session() as session:
        if item_type == 'paincase':
            result = await session.scalars(select(PainCase).where(PainCase.id == item_id))
            item = result.unique().first()
        elif item_type == 'druguse':
            result = await session.scalars(select(DrugUse).where(DrugUse.id == item_id))
            item = result.unique().first()
        elif item_type == 'pressure':
            result = await session.scalars(select(Pressure).where(Pressure.id == item_id))
            item = result.unique().first()
        elif item_type == 'drug':
            result = await session.scalars(select(Drug).where(Drug.id == item_id))
            item = result.unique().first()
        else:
            raise ValueError(f'Unknown item_type {item_type}')
    return item


async def delete_item(item) -> None:
    async with get_session() as session:
        await session.delete(item)
