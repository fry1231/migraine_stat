from aiogram import types
from aiogram.dispatcher.filters.state import State
from src.bot import dp

from db.redis.crud import add_user_to_state


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
        await add_user_to_state(f'{group_name}:{state_index}:{state_name}', types.User.get_current().id)
