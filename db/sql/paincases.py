import calendar
import datetime

from sqlalchemy import select, and_

from db.sql import get_session
from db.models import PainCase, DrugUse
from db.redis.crud import update_everyday_report


async def report_paincase(owner_id: int,
                          date: datetime.date | str,
                          durability: int,
                          intensity: int,
                          aura: bool,
                          provocateurs: str = None,
                          symptoms: str = None,
                          description: str = None,
                          drugname: list[str] = None,
                          amount: list[str] = None) -> PainCase:
    async with get_session() as session:
        # Ensure SmallInt in Postgres
        if abs(intensity) > 32000:
            intensity = 32000 if intensity > 0 else -32000
        if abs(durability) > 32000:
            durability = 32000 if durability > 0 else -32000
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, '%d.%m.%Y').date()
        db_pain = PainCase(date=date, durability=durability, intensity=intensity, aura=aura,
                           provocateurs=provocateurs, symptoms=symptoms, description=description, owner_id=owner_id)
        if drugname and amount:
            for i in range(len(drugname)):
                an_amount = amount[i]
                a_drugname = drugname[i]
                db_druguse = DrugUse(date=date, amount=an_amount, owner_id=owner_id, drugname=a_drugname)
                db_pain.medecine_taken.append(db_druguse)
        session.add(db_pain)
        await update_everyday_report(n_pains=1)
        return db_pain


async def get_user_pains(user_id: int,
                         period_days: int = -1,
                         date: datetime.date = None) -> list[PainCase]:
    async with get_session() as session:
        if date:
            result = await session.scalars(
                select(PainCase)
                .where(and_(
                    PainCase.owner_id == user_id,
                    PainCase.date == date
                ))
                .order_by(PainCase.date.asc())
            )
            db_pains = result.unique().all()
            return db_pains
        if period_days != -1:
            date_from = datetime.date.today() - datetime.timedelta(days=period_days)
            result = await session.scalars(
                select(PainCase)
                .where(and_(
                    PainCase.owner_id == user_id,
                    PainCase.date >= date_from
                ))
                .order_by(PainCase.date.desc())
            )
            db_pains = result.unique().all()
        else:
            result = await session.scalars(
                select(PainCase)
                .where(PainCase.owner_id == user_id)
                .order_by(PainCase.date.desc())
            )
            db_pains = result.unique().all()
    return db_pains


async def user_pain_days(user_id: int,
                         month: int,
                         year: int) -> list[int]:
    async with get_session() as session:
        date_from = datetime.date(year, month, 1)
        # Get the last day of the month
        __, last_day = calendar.monthrange(year, month)
        date_to = datetime.date(year, month, last_day)
        result = await session.scalars(
            select(PainCase.date)
            .where(
                and_(
                    PainCase.owner_id == user_id,
                    PainCase.date >= date_from,
                    PainCase.date <= date_to
                )))
        db_pains = result.all()
    return [el.day for el in db_pains]
