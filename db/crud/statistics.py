from sqlalchemy import select, func, and_
from typing import Type
import datetime

from db.crud import get_session
from db.models import SavedUser, SavedPressure, SavedDrugUse, SavedPainCase, Base


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
