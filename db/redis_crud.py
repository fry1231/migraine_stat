import orjson

from src.config import logger, redis_conn
from db.redis_models import PydanticUser, EverydayReport


async def init_everyday_report():
    await redis_conn.set('everyday_report',
                         EverydayReport(
                             n_notified_users=0,
                             new_users=[],
                             deleted_users=[],
                             n_pains=0,
                             n_druguses=0,
                             n_pressures=0,
                             n_medications=0
                         ).json())


async def get_current_report() -> EverydayReport:
    current_report = await redis_conn.get('everyday_report')
    if current_report:
        current_report = orjson.loads(current_report)
        return EverydayReport(**current_report)
    else:
        await init_everyday_report()
        logger.info('New everyday report initialized in Redis')
        return await get_current_report()


async def update_everyday_report(n_notified_users: int = 0,
                                 new_users: list[PydanticUser] = None,
                                 deleted_users: list[PydanticUser] = None,
                                 n_pains: int = 0,
                                 n_druguses: int = 0,
                                 n_pressures: int = 0,
                                 n_medications: int = 0):
    current_report = await get_current_report()
    current_report.n_notified_users += n_notified_users
    if new_users:
        current_report.new_users += new_users
    if deleted_users:
        current_report.deleted_users += deleted_users
    current_report.n_pains += n_pains
    current_report.n_druguses += n_druguses
    current_report.n_pressures += n_pressures
    current_report.n_medications += n_medications
    await redis_conn.set('everyday_report', current_report.json())
