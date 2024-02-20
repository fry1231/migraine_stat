import calendar
import datetime
from sqlalchemy import select, and_, func

from db.crud import get_session
from db.models import DrugUse
from db.redis_crud import update_everyday_report


async def report_druguse(date: datetime.date | str,
                         amount: str,
                         owner_id: int,
                         drugname: str,
                         paincase_id: int = None) -> DrugUse:
    async with get_session() as session:
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, '%d.%m.%Y').date()
        db_druguse = DrugUse(date=date, amount=amount, owner_id=owner_id, drugname=drugname, paincase_id=paincase_id)
        session.add(db_druguse)
        await update_everyday_report(n_druguses=1)
    return db_druguse


async def get_user_druguses(user_id: int,
                            period_days: int = -1,
                            date: datetime.date = None) -> list[DrugUse]:
    async with get_session() as session:
        if date:
            result = await session.scalars(
                select(DrugUse)
                .where(and_(
                    DrugUse.owner_id == user_id,
                    DrugUse.date == date
                ))
                .order_by(DrugUse.date.asc()))
            db_druguses = result.all()
            return db_druguses
        if period_days != -1:
            date_from = datetime.date.today() - datetime.timedelta(days=period_days)
            result = await session.scalars(
                select(DrugUse)
                .where(and_(
                    DrugUse.owner_id == user_id,
                    DrugUse.date >= date_from
                ))
                .order_by(DrugUse.date.desc()))
            db_druguses = result.all()
        else:
            result = await session.scalars(
                select(DrugUse)
                .where(DrugUse.owner_id == user_id)
                .order_by(DrugUse.date.desc()))
            db_druguses = result.all()
    return db_druguses


async def user_druguse_days(user_id: int,
                            month: int,
                            year: int) -> list[int]:
    async with get_session() as session:
        date_from = datetime.date(year, month, 1)
        # Get the last day of the month
        __, last_day = calendar.monthrange(year, month)
        date_to = datetime.date(year, month, last_day)
        result = await session.scalars(
            select(DrugUse.date)
            .where(and_(
                 DrugUse.owner_id == user_id,
                 DrugUse.date >= date_from,
                 DrugUse.date <= date_to
            )))
        db_druguses = result.all()
    return [el.day for el in db_druguses]
