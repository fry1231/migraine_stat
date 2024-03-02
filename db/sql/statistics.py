from sqlalchemy import select, func, and_
from typing import Type
import datetime

from db.sql import get_session
from db.sql.users import get_users
from db.models import Base, Statistics
from db.redis.models import EverydayReport


async def get_all_(table: Type[Base],
                   date_lt: datetime.date = None,
                   date_gt: datetime.date = None,
                   return_count: bool = False) -> list[Type[Base]] | int:
    async with get_session() as session:
        if return_count:
            stmt = select(func.count()).select_from(table)
        else:
            stmt = select(table)
        if date_lt:
            stmt = stmt.where(table.date < date_lt)
        if date_gt:
            stmt = stmt.where(table.date > date_gt)
        if return_count:
            result = await session.scalar(stmt)
            return result
        else:
            result = await session.scalars(stmt)
            entities = result.unique().all()
            return entities


async def report_everyday_stats(report: EverydayReport) -> None:
    async with get_session() as session:
        n_active_users = await get_users(active=True, return_count=True)
        n_super_active_users = await get_users(super_active=True, return_count=True)
        session.add(
            Statistics(
                date=datetime.date.today(),
                new_users=len(report.new_users),
                deleted_users=len(report.deleted_users),
                active_users=n_active_users,
                super_active_users=n_super_active_users,
                paincases=report.n_pains,
                druguses=report.n_druguses,
                pressures=report.n_pressures,
                medications=report.n_medications
            )
        )
