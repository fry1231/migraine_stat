from aiogram import types
from aiogram.dispatcher.filters import BoundFilter
from src.config import MY_TG_ID, logger
import os


class IsAdmin(BoundFilter):
    async def check(self, message_or_query: types.Message | types.CallbackQuery):
        return message_or_query.from_user.id == MY_TG_ID


class MaintenanceMode(BoundFilter):
    async def check(self, message: types.Message):
        is_admin = message.from_user.id == MY_TG_ID
        return os.getenv('MAINTENANCE') == '1' and not is_admin
