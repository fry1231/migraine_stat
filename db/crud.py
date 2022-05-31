from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from .models import User, PainCase, DrugUse, Drug
from .database import SessionLocal, engine


session = SessionLocal()


def wrap_session(db):
    def wrapper(add_func):
        def inner(*args, **kwargs):
            with db.begin():
                return add_func(*args, **kwargs)
        return inner
    return wrapper


# Users ==================================
def get_user(telegram_id: int):
    db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    return db_user


def get_users():
    return session.query(User).all()


def create_user(telegram_id: str,
                notify_every: int):
    db_user = User(telegram_id=telegram_id, notify_every=notify_every, last_notified=datetime.min)
    session.add(db_user)
    return db_user


def reschedule(telegram_id: str,
               notify_every: int):
    db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    db_user.notify_every = notify_every
    return db_user


# Paincases ====================================
def report_paincase(who: int,
                    when: datetime,
                    durability: int,
                    intensity: int,
                    aura: bool,
                    provocateurs: str,
                    symptoms: str,
                    description: str,
                    drugname: str = None,
                    amount: int = None,
                    **kwargs):
    db_pain = PainCase(datetime=when, durability=durability, intensity=intensity, aura=aura,
                       provocateurs=provocateurs, symptoms=symptoms, description=description)
    if drugname and amount:
        db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname)
        db_pain.medecine_taken.append(db_druguse)
    session.add(db_pain)
    return db_pain


def get_user_pains(user_id: int,
                   period_days: int = -1):
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
    db_druguse = DrugUse(datetime=when, amount=amount, owner_id=who, drugname=drugname, paincase_id=paincase_id)
    session.add(db_druguse)
    return db_druguse


def get_user_druguses(user_id: int,
                      period_days: int = -1):
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
             is_temp_reducer: bool):
    db_drug = Drug(name=name, daily_max=daily_max, is_painkiller=is_painkiller, is_temp_reducer=is_temp_reducer)
    session.add(db_drug)
    return db_drug


def get_drugs():
    db_drugs = session.query(Drug).all()
    return db_drugs
