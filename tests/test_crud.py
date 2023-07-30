import pytest
from datetime import datetime
import os

os.environ["IS_TESTING"] = '1'

from db.models import User
from db.database import Base, test_engine
from db import crud


@pytest.fixture(scope="session", autouse=True)
def resource():
    """
    Force crud operations to perform on a test database "sqlite:///db/test.db"
    Creates all necessary tables at the beginning of the testing and drops them in the end
    """
    assert crud.use_engine.url.database == 'db/test.db'
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    os.environ["IS_TESTING"] = '0'
    Base.metadata.drop_all(test_engine)


async def test_create_user():
    # Create a new user
    user = await crud.create_user(
        telegram_id=123,
        notify_every=1,
        first_name='Lorem',
        user_name='Ipsum'
    )

    # Check if the user exists in the database
    added_user: User = await crud.get_user(telegram_id=123)
    assert user is not None
    assert user.first_name == added_user.first_name


async def batch_change_last_notified(session, datetime_check):
    # Add second user, 2 users overall
    await crud.create_user(
        telegram_id=456,
        notify_every=1,
        first_name='QQ',
        user_name='WW'
    )

    # Change last notified
    notif_time = datetime.now()
    await crud.batch_change_last_notified(
        telegram_ids=[123, 456],
        time_notified=notif_time
    )

    # Verify
    users: list[User] = await crud.get_users()
    assert len(users) == 2
    for user in users:
        assert user.last_notified == notif_time
