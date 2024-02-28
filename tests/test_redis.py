import os

os.environ["IS_TESTING"] = '1'

import pytest
import asyncio
from db.redis.models import PydanticUser, EverydayReport
from db.redis.crud import update_everyday_report, get_current_report
from src.misc.service_reports import notif_of_new_users
from src.config import redis_conn


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def resource():
    assert redis_conn.connection_pool.connection_kwargs['db'] == 5
    await redis_conn.flushdb()

    yield

    await redis_conn.flushdb()
    os.environ["IS_TESTING"] = '0'


async def test_send_messages():
    new_users = [PydanticUser(telegram_id=123123123121 + i,
                              first_name=str(i) + 'QQ',
                              last_name=str(i)+'кириллические буковки и $|^|EЦ3Haku!',
                              user_name=str(i)+'EE')
                 for i in range(5)]
    for user in new_users:
        await update_everyday_report(new_users=[user])


async def test_notification_new_users():
    text = await notif_of_new_users()
    assert "5 new users:\n1. 123123123121" in text and '4QQ' in text
