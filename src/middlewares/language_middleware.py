from aiogram import types
from aiogram.contrib.middlewares.i18n import I18nMiddleware
import traceback

from db.sql import get_user
from db.models import User
from src.config import redis_conn, logger


async def get_user_language(curr_user: types.User) -> str:
    """
    Get user language from Redis or DB if not found in Redis
    :param curr_user: User object
    :return: user language 2-letter code (or maybe 3)
    """
    user_id = curr_user.id
    language = await redis_conn.get(str(user_id))
    if language is None:
        user: User = await get_user(user_id)
        if user:
            language = user.language
        else:
            language = curr_user.locale.language
            if language not in ['ru', 'uk', 'en', 'fr', 'es']:
                logger.warning(f'Unsupported language: {language}')
                if language in ['hy', 'az', 'uz', 'kk', 'ky', 'tk', 'tt', 'tg', 'mn', 'ba', 'cv', 'udm', 'sah', 'kbd',
                                'krc', 'ab', 'os', 'ce', 'ady', 'mhr', 'xal', 'kkj', 'koi', 'kum', 'av', 'tyv', 'alt',
                                'sah', 'chm', 'inh', 'bua']:
                    language = 'ru'
                else:
                    language = 'en'
        await redis_conn.set(str(user_id), language)
    return language


class CustomI18nMiddleware(I18nMiddleware):
    """Custom I18n middleware with get_user_locale method overriden to get user locale from Redis"""
    async def get_user_locale(self, action: str, args: tuple) -> str:
        """
        User locale getter
        You can override the method if you want to use different way of
        getting user language.

        :param action: event name
        :param args: event arguments
        :return: locale name
        """
        curr_user = types.User.get_current()   # TODO: Why None sometimes?
        stack = "\n".join(traceback.format_stack())
        if curr_user is None:
            logger.error(f'User is None. Call stack: {stack}')
            return 'ru'
        language = await get_user_language(curr_user)
        return language
