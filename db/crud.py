import traceback
from contextlib import contextmanager
import datetime
from src.bot import bot
from .models import User, PainCase, DrugUse, Drug, SavedDrugUse, SavedPainCase
from .database import engine, test_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_, not_
from sqlalchemy import text as raw_query
from typing import List
import asyncio
from functools import wraps
from src.settings import IS_TESTING, MY_TG_ID


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
def get_session() -> SessionLocal:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        try:
            asyncio.run(bot.send_message(chat_id=MY_TG_ID, text=f'Error while CRUD:\n\n{traceback.format_exc()}'))
        except Exception:
            pass
    else:
        session.commit()
    finally:
        session.close()


@to_async
def healthcheck():
    with get_session() as session:
        try:
            session.execute(raw_query('SELECT 1'))
            return True
        except Exception:
            return False


# Users ==================================
@to_async
def get_user(telegram_id: int) -> User:
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return db_user


@to_async
def get_users() -> list[User]:
    with get_session() as session:
        return session.query(User).all()


@to_async
def create_user(telegram_id: int,
                first_name: str,
                user_name: str,
                language: str = 'ru') -> User:
    with get_session() as session:
        db_user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            user_name=user_name,
            joined=datetime.date.today(),
            language=language
        )
        session.add(db_user)
        return db_user


@to_async
def delete_user(telegram_id: int) -> bool:
    with get_session() as session:
        db_user: User = session.query(User).filter(User.telegram_id == telegram_id).first()

        # Get all user pains and druguses
        user_pains: list[PainCase] = session.query(PainCase).filter(PainCase.owner_id == db_user.telegram_id).all()
        associated_druguses: list[DrugUse] = []
        for pain in user_pains:
            for du in pain.medecine_taken:
                associated_druguses.append(du)
        # Child druguses of paincases
        associated_druguses_ids: list[int] = [el.id for el in associated_druguses]
        # Druguses, nonassociated with paincases
        nonassoc_druguses: list[DrugUse] = session.query(DrugUse).filter(
            DrugUse.id.not_in(associated_druguses_ids)).all()

        # Save them to "Saved..." tables
        to_add: list[SavedPainCase or SavedDrugUse] = []
        to_add += [SavedPainCase.copy_from(el) for el in user_pains]
        to_add += [SavedDrugUse.copy_from(el) for el in nonassoc_druguses]
        session.add_all(to_add)

        # Cascade delete user and associated objects from the main tables
        session.delete(db_user)
        return True


@to_async
def reschedule(telegram_id: int,
               notify_every: int) -> None:
    with get_session() as session:
        db_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        db_user.notify_every = notify_every


@to_async
def batch_change_last_notified(telegram_ids: List[int],
                               time_notified: datetime.datetime) -> None:
    with get_session() as session:
        session.query(User).filter(
            User.telegram_id.in_(telegram_ids)
        ).update({
            User.last_notified: time_notified
        }, synchronize_session=False)


# Paincases ====================================
@to_async
def report_paincase(owner_id: int,
                    date: datetime.date,
                    durability: int,
                    intensity: int,
                    aura: bool,
                    provocateurs: str = None,
                    symptoms: str = None,
                    description: str = None,
                    drugname: list[str] = None,
                    amount: list[str] = None) -> PainCase:
    with get_session() as session:
        # Limit to match SmallInt in Postgres
        if abs(intensity) > 32000:
            intensity = 32000 if intensity > 0 else -32000
        if abs(durability) > 32000:
            durability = 32000 if durability > 0 else -32000

        db_pain = PainCase(date=date, durability=durability, intensity=intensity, aura=aura,
                           provocateurs=provocateurs, symptoms=symptoms, description=description, owner_id=owner_id)
        if drugname and amount:
            for i in range(len(drugname)):
                an_amount = amount[i]
                a_drugname = drugname[i]
                db_druguse = DrugUse(date=date, amount=an_amount, owner_id=owner_id, drugname=a_drugname)
                db_pain.medecine_taken.append(db_druguse)
        session.add(db_pain)
        return db_pain


@to_async
def get_user_pains(user_id: int,
                   period_days: int = -1) -> list[PainCase]:
    with get_session() as session:
        if period_days != -1:
            date_from = datetime.date.today() - datetime.timedelta(days=period_days)
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id)\
                                              .filter(PainCase.date >= date_from)\
                                              .all()
        else:
            db_pains = session.query(PainCase).filter(PainCase.owner_id == user_id).all()
        return db_pains


@to_async
def get_user_ids_pains() -> list[int]:
    with get_session() as session:
        user_ids: list[tuple] = session.query(PainCase.owner_id).all()
        return [el[0] for el in user_ids]


# Druguses ====================================
@to_async
def report_druguse(date: datetime.date,
                   amount: str,
                   owner_id: int,
                   drugname: str,
                   paincase_id: int = None) -> DrugUse:
    with get_session() as session:
        db_druguse = DrugUse(date=date, amount=amount, owner_id=owner_id, drugname=drugname, paincase_id=paincase_id)
        session.add(db_druguse)
        return db_druguse


@to_async
def get_user_druguses(user_id: int,
                      period_days: int = -1) -> list[DrugUse]:
    with get_session() as session:
        if period_days != -1:
            date_from = datetime.date.today() - datetime.timedelta(days=period_days)
            db_druguses = session.query(DrugUse).filter(DrugUse.owner_id == user_id)\
                                                .filter(DrugUse.date >= date_from)\
                                                .all()
        else:
            db_druguses = session.query(DrugUse).filter(DrugUse.owner_id == user_id).all()
        return db_druguses


# Drugs ====================================
@to_async
def add_drug(name: str,
             daily_max: int,
             is_painkiller: bool,
             is_temp_reducer: bool,
             user_id: int) -> Drug:
    with get_session() as session:
        db_drug = Drug(name=name,
                       daily_max=daily_max,
                       is_painkiller=is_painkiller,
                       is_temp_reducer=is_temp_reducer,
                       owner_id=user_id)
        session.add(db_drug)
        return db_drug


@to_async
def get_drugs(owner: int = None) -> list[Drug]:
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
