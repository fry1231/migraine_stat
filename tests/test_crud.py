import asyncio

import pytest
import datetime
import os
from sqlalchemy_utils import create_database, database_exists

os.environ["IS_TESTING"] = '1'

from db.models import User, Drug, DrugUse, PainCase, SavedDrugUse, SavedPainCase
from db.models import Base
from db.database import test_engine
from db import crud


@pytest.fixture(scope="session", autouse=True)
def resource():
    """
    Force crud operations to perform on a test database "sqlite:///db/db_file/test.db"
    Creates all necessary tables at the beginning of the testing and drops them in the end
    """
    if not database_exists(test_engine.url):
        create_database(test_engine.url)
    assert 'db_test' in crud.use_engine.url.database, f'URL database is not db_test ' \
                                                      f'({crud.use_engine.url.database})'
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    os.environ["IS_TESTING"] = '0'
    Base.metadata.drop_all(test_engine)


async def test_create_user():
    # Create a new user
    user = await crud.create_user(
        telegram_id=123,
        first_name='Lorem',
        user_name='Ipsum'
    )

    # Check if the user exists in the database
    added_user: User = await crud.get_user(telegram_id=123)
    assert user is not None
    assert user.first_name == added_user.first_name
    assert user.notify_every == -1


async def test_batch_change_last_notified():
    # Add second user, 2 users overall
    await crud.create_user(
        telegram_id=456,
        first_name='QQ',
        user_name='WW'
    )

    # Change last notified
    notif_time = datetime.datetime.now()
    await crud.batch_change_last_notified(
        telegram_ids=[123, 456],
        time_notified=notif_time
    )

    # Verify
    users: list[User] = await crud.get_users()
    assert len(users) == 2
    for user in users:
        assert user.last_notified == notif_time


async def test_add_drug():
    await crud.add_drug(
        name='Aspirin',
        daily_max=200,
        is_painkiller=True,
        is_temp_reducer=False,
        user_id=123
    )
    drugs: list[Drug] = await crud.get_drugs(owner=123)
    assert len(drugs) == 1
    assert drugs[0].owner_id == 123


class TestPaincases:
    data = dict(
        date=datetime.date(2020, 1, 1),
        durability=2,
        intensity=5,
        aura=False,
        provocateurs='p1, p2',
        symptoms=None,
        description='not empty',
        owner_id=123,
    )
    druguse_data = dict(
        amount=['200'],
        drugname=['Aspirin']
    )
    druguse_data_several = dict(
        amount=['200', '1 pill'],
        drugname=['Парацетамол;Â, Ê, Î, Ô, Û, Ä, Ë, Ï, Ö, Ü, À, Æ, æ, Ç, É', 'Ibuprofen']
    )

    async def test_without_druguse(self):
        await crud.report_paincase(**self.data)
        paincases: list[PainCase] = await crud.get_user_pains(user_id=123)
        assert len(paincases) == 1
        assert len(paincases[0].medecine_taken) == 0

    async def test_with_1_druguse(self):
        test_data = {**self.data, **self.druguse_data}
        commited_pc: PainCase = await crud.report_paincase(**test_data)
        paincases: list[PainCase] = await crud.get_user_pains(user_id=123)
        assert len(paincases) == 2
        pc_from_db = [pc for pc in paincases if pc.id == commited_pc.id][0]
        assert len(pc_from_db.medecine_taken) == 1

    async def test_with_many_druguse(self):
        test_data = {**self.data, **self.druguse_data_several}
        commited_pc: PainCase = await crud.report_paincase(**test_data)
        paincases: list[PainCase] = await crud.get_user_pains(user_id=123)
        assert len(paincases) == 3
        pc_from_db = [pc for pc in paincases if pc.id == commited_pc.id][0]
        assert len(pc_from_db.medecine_taken) == 2


async def test_druguses():
    data = dict(
        date=datetime.date(2020, 1, 1),
        amount='100',
        drugname='ColaZero',
        owner_id=123
    )
    await crud.report_druguse(**data)
    await crud.report_druguse(**data)   # 2nd time so user(123) has 3 paincases and 5 druguses
    druguses: list[DrugUse] = await crud.get_user_druguses(user_id=123)
    assert len(druguses) == 5
    assert druguses[0].drugname == 'Aspirin'
    assert druguses[-1].drugname == 'ColaZero'


async def test_users_info_after_deletion():
    await crud.delete_user(telegram_id=123)
    users = await crud.get_users()
    user_paincases = await crud.get_user_pains(user_id=123)
    user_drugs = await crud.get_drugs(owner=123)
    user_druguses = await crud.get_user_druguses(user_id=123)

    assert len(users) == 1
    assert len(user_paincases) == 0
    assert len(user_drugs) == 0
    assert len(user_druguses) == 0

    with crud.get_session() as session:
        saved_druguses: list[SavedDrugUse] = session.query(SavedDrugUse).all()
        saved_paincases: list[SavedPainCase] = session.query(SavedPainCase).all()

    assert len(saved_paincases) == 3
    assert len(saved_druguses) == 5


# async def test_multiple_connections():
#     await asyncio.gather(
#         *[
#             crud.create_user(
#                 telegram_id=i,
#                 first_name=str(i) + 'QQ',
#                 user_name=str(i) + 'WW'
#             ) for i in range(1000, 2000)
#         ]
#     )
