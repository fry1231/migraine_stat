from contextlib import contextmanager
from datetime import datetime, date, timedelta
from .models import User, PainCase, DrugUse, Drug
from .database import engine, test_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, not_
from sqlalchemy import text as raw_query
from typing import List
import asyncio
from functools import wraps
from src.settings import IS_TESTING


if IS_TESTING:
    use_engine = test_engine
else:
    use_engine = engine

SessionLocal = sessionmaker(
    use_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=True,
    # future=True
)


def to_async(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    else:
        session.commit()
    finally:
        session.close()


# Users ==================================
@to_async
def get_user(telegram_id: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return db_user


@to_async
def get_users():
    with get_session() as session:
        return session.query(User).all()


@to_async
def create_user(telegram_id: int,
                notify_every: int,
                first_name: str,
                user_name: str):
    with get_session() as session:
        db_user = User(telegram_id=telegram_id,
                       notify_every=notify_every,
                       last_notified=datetime.min,
                       first_name=first_name,
                       user_name=user_name)
        session.add(db_user)
        return db_user


@to_async
def delete_user(telegram_id: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        session.delete(db_user)
        return True


@to_async
def reschedule(telegram_id: int,
               notify_every: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        db_user.notify_every = notify_every
        return db_user


@to_async
def change_last_notified(telegram_id: int,
                         time_notified: datetime):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        db_user.last_notified = time_notified
        return db_user


@to_async
def batch_change_last_notified(telegram_ids: List[int],
                               time_notified: datetime):
    with get_session() as session:
        session.query(User).filter(
            User.telegram_id.in_(telegram_ids)
        ).update({
            User.last_notified: time_notified
        }, synchronize_session=False)


# Paincases ====================================
@to_async
def report_paincase(who: int,
                    when: datetime,
                    durability: int,
                    intensity: int,
                    aura: bool,
                    provocateurs: str = None,
                    symptoms: str = None,
                    description: str = None,
                    drugname: str = None,
                    amount: str = None,
                    **kwargs):
    with get_session() as session:
        db_pain = PainCase(datetime=when, durability=durability, intensity=intensity, aura=aura,
                           provocateurs=provocateurs, symptoms=symptoms, description=description, owner_id=who)
        if drugname and amount:
            db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname)
            db_pain.medecine_taken.append(db_druguse)
        session.add(db_pain)
        return db_pain


@to_async
def get_user_pains(user_id: int,
                   period_days: int = -1):
    with get_session() as session:
        if period_days != -1:
            date_from = date.today() - timedelta(days=period_days)
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id).filter(PainCase.datetime >= date_from)
        else:
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id)
        return db_pains


@to_async
def get_user_ids_pains():
    with get_session() as session:
        return session.query(PainCase.owner_id).all()


# Druguses ====================================
@to_async
def report_druguse(when: datetime,
                   amount: int,
                   who: int,
                   drugname: str,
                   paincase_id: int = None):
    with get_session() as session:
        db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname, paincase_id=paincase_id)
        session.add(db_druguse)
        return db_druguse


@to_async
def get_user_druguses(user_id: int,
                      period_days: int = -1):
    with get_session() as session:
        if period_days != -1:
            date_from = date.today() - timedelta(days=period_days)
            db_druguses = session.query(DrugUse).filter(DrugUse.owner_id == user_id).filter(DrugUse.datetime >= date_from)
        else:
            db_druguses = session.query(DrugUse).filter(DrugUse.owner_id == user_id)
        return db_druguses


# Drugs ====================================
@to_async
def add_drug(name: str,
             daily_max: int,
             is_painkiller: bool,
             is_temp_reducer: bool,
             user_id: int):
    with get_session() as session:
        db_drug = Drug(name=name,
                       daily_max=daily_max,
                       is_painkiller=is_painkiller,
                       is_temp_reducer=is_temp_reducer,
                       owner_id=user_id)
        session.add(db_drug)
        return db_drug


@to_async
def get_drugs(owner: int = None):
    with get_session() as session:
        if owner:
            db_drugs = session.query(Drug).filter(
                or_(
                    Drug.owner_id == owner,
                    Drug.owner_id == -1
                )
            ).all()
        else:
            db_drugs = session.query(Drug).all()
        return db_drugs


@to_async
def execute_raw(command: str):
    sql = raw_query(command)
    results = engine.execute(sql)
    if results is not None:
        return results
    return 'Executed successfully'
