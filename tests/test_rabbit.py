import os

os.environ["IS_TESTING"] = '1'

import pytest
from src.messages_handler import postpone_new_user_notif, notif_of_new_users
from db.models import NewUser


@pytest.fixture(scope="session", autouse=True)
def resource():
    yield
    os.environ["IS_TESTING"] = '0'


async def test_send_messages():
    new_users = [NewUser(first_name=str(i)+'QQ',
                         last_name=str(i)+'кириллические буковки и $|^|EЦ3Haku!',
                         user_name=str(i)+'EE')
                 for i in range(5)]
    for user in new_users:
        await postpone_new_user_notif(user)


async def test_notification_new_users():
    text = await notif_of_new_users()
    assert "5 new users:\n0QQ" in text
