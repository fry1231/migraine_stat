import orjson

from src.config import logger, redis_conn
from db.redis.models import PydanticUser, EverydayReport, StateUpdate

### Language:
# User language is stored under the key 'user_id'

### States:
# User's current_state (within fsm forms) is stored under the key 'user_state:user_id'
# All user states are stored under the keys 'state:*'. List of all available states are in fsm_forms/__init__.py
# # Channels:
# If some state is changing, a message is sent to 'channel:states' to reflect the changes:
# {
#     "user_id": 123,
#     "user_state": "AddDrugForm:0:name",
#     "action": "set", (or "unset")
#     "incr_value": 1
# }
# Each subsequent message increments 'incr_value' by 1. Current increment value is stored under the 'incr_value' key
# If 'incr_value' == 0, then it is needed to request all the states from API

### Everyday report:
# If everyday report is changed, message is sent to 'channel:report' to reflect the changes:
# {
#         "n_notified_users": 0,
#         "new_users": [list of PydanticUser],
#         "deleted_users": [list of PydanticUser],
#         "n_pains": 0,
#         "n_druguses": 0,
#         "n_pressures": 0,
#         "n_medications": 0
# }


async def init_everyday_report():
    report = EverydayReport(
        n_notified_users=0,
        new_users=[],
        deleted_users=[],
        n_pains=0,
        n_druguses=0,
        n_pressures=0,
        n_medications=0
    )
    await redis_conn.set('everyday_report', report.json())
    await redis_conn.publish('channel:report', report.json())


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
    await redis_conn.publish('channel:report', current_report.json())


async def send_state_update(user_id: int, user_state: str, action: str) -> None:
    if action not in ['set', 'unset']:
        logger.error(f'Invalid action {action} for user {user_id} and state {user_state}')
        return
    # Get current increment value, set the next incr to current_incr + 1
    current_incr = await redis_conn.get('incr_value')
    if not current_incr:
        next_incr = 0
        await redis_conn.set('incr_value', next_incr)
    else:
        current_incr = int(current_incr)
        next_incr = current_incr + 1
        await redis_conn.set('incr_value', next_incr)
    await redis_conn.publish('channel:states',
                             StateUpdate(
                                 user_id=user_id,
                                 user_state=user_state,
                                 action=action,
                                 incr_value=next_incr)
                             .json())


async def add_user_to_state(state_name: str, user_id: int):
    """
    States are used to store users who are in the process of filling out a form
    State: state_name, Value: list[int] of user_ids
    :param state_name:
    :param user_id:
    :return:
    """
    # Clear previous state
    await remove_user_state(user_id)
    # Add user to state
    if not await redis_conn.exists(f'state:{state_name}'):
        logger.warning(f'No state {state_name} found in Redis')
        state_users = [user_id]
    else:
        state_users = await redis_conn.get(f'state:{state_name}')
        state_users = orjson.loads(state_users)
        state_users.append(user_id)
    await redis_conn.set(state_name, orjson.dumps(state_users))
    # Add current_state to user_state
    await redis_conn.set(f'user_state:{user_id}', state_name)
    await send_state_update(user_id, state_name, 'set')


async def remove_user_state(user_id: int) -> None:
    """
    Used to remove user from state when user has finished filling out the form or to clear previous state
    """
    # Remove current_state from user_state
    if not await redis_conn.exists(f'user_state:{user_id}'):
        return
    current_state = await redis_conn.get(f'user_state:{user_id}')

    # Remove user_id from state
    if not await redis_conn.exists(f'state:{current_state}'):
        logger.warning(f'No state {current_state} found in Redis')
        return

    state_users = await redis_conn.get(f'state:{current_state}')
    state_users = orjson.loads(state_users)
    while user_id in state_users:
        state_users.remove(user_id)
    await redis_conn.delete(f'user_state:{user_id}')
    await redis_conn.set(f'state:{current_state}', orjson.dumps(state_users))
    await send_state_update(user_id, current_state, 'unset')


async def init_states(fsm_states) -> None:
    """
    Initialize states in Redis, prefixed with 'state:'
    """
    for state in fsm_states:
        key = f'state:{state}'
        if not await redis_conn.exists(key):
            await redis_conn.set(key, '[]')
            logger.debug(f'Initialized state {state}')
    # Publish update to channel, incr_value = 0 to trigger update of all states on client side
    await redis_conn.publish('channel:states',
                             StateUpdate(user_id=0,
                                         user_state='null',
                                         action='refresh',
                                         incr_value=0).json())
    await redis_conn.set('incr_value', 0)
