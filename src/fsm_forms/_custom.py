from aiogram import types
from aiogram.dispatcher.filters.state import State
import asyncio

from src.bot import dp
from db.redis.crud import add_user_to_state, remove_user_state


async def delayed(delay: int, action: callable, *args, **kwargs):
    """
    Delayed action
    :param delay: delay in seconds
    :param action: action to be performed
    :param args: arguments for the action
    """
    await asyncio.sleep(delay)
    await action(*args, **kwargs)


class CustomState(State):
    """
    Custom State class
    Along with setting the state in StatesGroup in FSM forms, also handles adding user to the state in Redis
    """
    async def set(self):
        state = dp.current_state()
        await state.set_state(self.state)
        group = self.group.get_root()
        state_index = group.states_names.index(self.state)
        group_name, state_name = self.state.split(':')

        user_id = types.User.get_current().id
        full_state_name = f'{group_name}:{state_index}:{state_name}'
        await add_user_to_state(full_state_name, user_id)
        asyncio.get_event_loop().create_task(
            delayed(120, remove_user_state, user_id=user_id, from_state=full_state_name)
        )
