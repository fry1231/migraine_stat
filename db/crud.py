from contextlib import contextmanager
from datetime import datetime, date, timedelta
from .models import User, PainCase, DrugUse, Drug
from .database import SessionLocal, engine
from sqlalchemy import and_, or_, not_
from sqlalchemy import text as raw_query


# def wrap_session(db):
#     def wrapper(add_func):
#         def inner(*args, **kwargs):
#             with db.begin():
#                 return add_func(*args, **kwargs)
#         return inner
#     return wrapper

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    except:
        session.rollback()
        raise
    else:
        session.commit()


# Users ==================================
def get_user(telegram_id: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return db_user


def get_users():
    with get_session() as session:
        return session.query(User).all()


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


def delete_user(telegram_id: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        session.delete(db_user)
        return True


def reschedule(telegram_id: int,
               notify_every: int):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        db_user.notify_every = notify_every
        return db_user


def change_last_notified(telegram_id: int, time_notified: datetime):
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        db_user.last_notified = time_notified
        return db_user


# Paincases ====================================
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


def get_user_pains(user_id: int,
                   period_days: int = -1):
    with get_session() as session:
        if period_days != -1:
            date_from = date.today() - timedelta(days=period_days)
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id).filter(PainCase.datetime >= date_from)
        else:
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id)
        return db_pains


# Druguses ====================================
def report_druguse(when: datetime,
                   amount: int,
                   who: int,
                   drugname: str,
                   paincase_id: int = None):
    with get_session() as session:
        db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname, paincase_id=paincase_id)
        session.add(db_druguse)
        return db_druguse


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


def execute_raw(command: str):
    sql = raw_query(command)
    results = engine.execute(sql)
    if results is not None:
        return results
    return 'Executed successfully'
