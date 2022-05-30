from sqlalchemy.orm import Session
from datetime import datetime
from .models import User, PainCase, DrugUse, Drug
from .database import SessionLocal


session = SessionLocal()


def wrap_session(db):
    def wrapper(add_func):
        def inner(*args, **kwargs):
            print(args)
            print(kwargs)
            with db.begin():
                return add_func(**kwargs)
        return inner
    return wrapper


# Users ==================================
@wrap_session(session)
def get_user(telegram_id: int):
    db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    return db_user


@wrap_session(session)
def get_users(skip: int = 0, limit: int = 1000):
    return session.query(User).offset(skip).limit(limit).all()


@wrap_session(session)
def create_user(telegram_id: str,
                notify_every: int):
    db_user = User(telegram_id=telegram_id, notify_every=notify_every, last_notified=datetime.min)
    session.add(db_user)
    return db_user


@wrap_session(session)
def reschedule(telegram_id: str,
               notify_every: int):
    db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    db_user.notify_every = notify_every
    return db_user


# Paincases ====================================
@wrap_session(db=session)
def report_paincase(when: datetime,
                    medecine: bool,
                    description: str,
                    who: int):
    db_pain = PainCase(datetime=when, medecine=medecine, description=description, owner_id=who)
    session.add(db_pain)
    return db_pain


@wrap_session(session)
def report_druguse(when: datetime,
                   amount: int,
                   who: int,
                   drugname: str,
                   paincase_id: int = None):
    db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname, paincase_id=paincase_id)
    session.add(db_druguse)
    return db_druguse


@wrap_session(session)
def add_drug(name: str,
             daily_max: int,
             is_painkiller: bool,
             is_temp_reducer: bool):
    db_drug = Drug(name=name, daily_max=daily_max, is_painkiller=is_painkiller, is_temp_reducer=is_temp_reducer)
    session.add(db_drug)
    return db_drug




#
# @wrap_session
# def create_user(db: Session,
#                 telegram_id: str,
#                 notify_every: int):
#     db_user = User(telegram_id=telegram_id, notify_every=notify_every)
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#     return db_user
#
#
# @wrap_session
# def report_paincase(db: Session,
#                     when: datetime,
#                     medecine: bool,
#                     description: str,
#                     who: int):
#     db_pain = PainCase(datetime=when, medecine=medecine, description=description, owner_id=who)
#     db.add(db_pain)
#     db.commit()
#     db.refresh(db_pain)
#     return db_pain
#
#
# @wrap_session
# def report_druguse(db: Session,
#                    when: datetime,
#                    amount: int,
#                    who: int,
#                    drugname: str,
#                    paincase_id: int = None):
#     db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname, paincase_id=paincase_id)
#     db.add(db_druguse)
#     db.commit()
#     db.refresh(db_druguse)
#     return db_druguse
#
#
# @wrap_session
# def add_drug(db: Session,
#              name: str,
#              daily_max: int,
#              is_painkiller: bool,
#              is_temp_reducer: bool):
#     db_drug = Drug(name=name, daily_max=daily_max, is_painkiller=is_painkiller, is_temp_reducer=is_temp_reducer)
#     db.add(db_drug)
#     db.commit()
#     db.refresh(db_drug)
#     return db_drug
#
#
# @wrap_session
# def get_user(telegram_id: int):
#     return db.query(User).filter(User.telegram_id == telegram_id).first()
#
#
# @wrap_session
# def get_users(skip: int = 0, limit: int = 100):
#     return db.query(User).offset(skip).limit(limit).all()
#
#
# # def get_items(db: Session, skip: int = 0, limit: int = 100):
# #     return db.query(models.Item).offset(skip).limit(limit).all()
#
#
