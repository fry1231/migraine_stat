import datetime

from sqlalchemy import select, and_

from db.sql import get_session
from db.redis.crud import update_everyday_report
from db.models import Pressure


async def report_pressure(systolic: int,
                          diastolic: int,
                          pulse: int,
                          owner_id: int) -> Pressure:
    async with get_session() as session:
        db_pressure = Pressure(datetime=datetime.datetime.utcnow(),
                               systolic=systolic,
                               diastolic=diastolic,
                               pulse=pulse,
                               owner_id=owner_id)
        session.add(db_pressure)
        await update_everyday_report(n_pressures=1)
    return db_pressure


async def get_user_pressures(user_id: int,
                             period_days: int = -1,
                             date: datetime.date = None) -> list[Pressure]:
    async with get_session() as session:
        if date:
            next_day = date + datetime.timedelta(days=1)
            _datetime = datetime.datetime.combine(date, datetime.datetime.min.time())
            result = await session.scalars(
                select(Pressure)
                .where(and_(
                    Pressure.owner_id == user_id,
                    Pressure.datetime >= date,
                    Pressure.datetime < next_day
                ))
                .order_by(Pressure.datetime.asc()))
            db_pressures = result.all()
            return db_pressures
        if period_days != -1:
            date_from = datetime.date.today() - datetime.timedelta(days=period_days)
            result = await session.scalars(
                select(Pressure)
                .where(and_(
                    Pressure.owner_id == user_id,
                    Pressure.datetime >= date_from
                ))
                .order_by(Pressure.datetime.desc()))
            db_pressures = result.all()
        else:
            result = await session.scalars(
                select(Pressure)
                .where(Pressure.owner_id == user_id)
                .order_by(Pressure.datetime.desc()))
            db_pressures = result.all()
    return db_pressures
