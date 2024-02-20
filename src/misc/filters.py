from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from src.config import MY_TG_ID


class IsAdmin(BoundFilter):
    async def check(self, message_or_query: types.Message | types.CallbackQuery):
        return message_or_query.from_user.id == MY_TG_ID
