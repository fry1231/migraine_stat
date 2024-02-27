from sqlalchemy import select, or_

from db.sql import get_session
from db.redis.crud import update_everyday_report
from db.models import Drug


async def add_drug(name: str,
                   daily_max: int,
                   is_painkiller: bool,
                   is_temp_reducer: bool,
                   user_id: int) -> Drug:
    async with get_session() as session:
        db_drug = Drug(name=name,
                       daily_max=daily_max,
                       is_painkiller=is_painkiller,
                       is_temp_reducer=is_temp_reducer,
                       owner_id=user_id)
        session.add(db_drug)
        await update_everyday_report(n_medications=1)
    return db_drug


async def delete_drug(drug_id: int) -> None:
    async with get_session() as session:
        result = await session.scalars(select(Drug).where(Drug.id == drug_id))
        db_drug = result.first()
        await session.delete(db_drug)


async def get_drugs(owner: int = None) -> list[Drug]:
    async with get_session() as session:
        if owner:
            result = await session.scalars(
                select(Drug)
                .where(or_(
                    Drug.owner_id == owner,
                    Drug.owner_id == -1
                )))
            db_drugs = result.all()
        else:
            result = await session.scalars(select(Drug))
            db_drugs = result.all()
    return db_drugs
