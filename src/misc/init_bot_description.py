from aiogram import types
from aiogram.utils.exceptions import RetryAfter
import sys
import asyncio

from src.bot import bot, _
from src.config import logger


async def set_bot_name():
    try:
        for locale in ['en', 'uk', 'fr', 'es', 'ru', None]:
            names = {
                'en': 'Migraine',
                'uk': 'Мігрень',
                'fr': 'Migraine',
                'es': 'Migraña',
                'ru': 'Migren',
                None: 'Migraine'
            }
            language_code = locale if locale else ''
            result = await bot.request(
                'setMyName',
                data={
                    'name': names[locale],
                    'language_code': language_code
                },
            )
            if not result:
                logger.error(f'Error while setting bot name to {names[locale]}')
    except RetryAfter:
        logger.error('RetryAfter error while setting bot name')


async def set_bot_commands():
    try:
        for locale in ['en', 'uk', 'fr', 'es', 'ru', None]:
            result = await bot.set_my_commands([
                types.bot_command.BotCommand('pain', _('запись бо-бо', locale=locale)),
                types.bot_command.BotCommand('druguse', _('приём лекарства', locale=locale)),
                types.bot_command.BotCommand('pressure', _('запись давления', locale=locale)),
                types.bot_command.BotCommand('medications', _('список лекарств', locale=locale)),
                types.bot_command.BotCommand('calendar', _('изменить записи', locale=locale)),
                types.bot_command.BotCommand('statistics', _('статистика', locale=locale)),
                types.bot_command.BotCommand('settings', _('настройки', locale=locale)),
            ], language_code=locale)
            if not result:
                logger.error(f'Error while setting bot commands for {locale}')
    except RetryAfter:
        logger.error('RetryAfter error while setting bot name')


async def set_bot_description():
    try:
        for locale in ['en', 'uk', 'fr', 'es', 'ru', None]:
            language_code = locale if locale else ''
            short_desc = {
                'ru': 'Бот для ведения дневника головных болей, приёма лекарств и давления\n'
                      'Для связи пишите прямо в бот',
                'en': 'Bot for tracking headache, medications intake and pressure\n'
                      'For support message the bot directly',
                'uk': 'Бот для ведення щоденника головних болей, прийому ліків та тиску\n'
                      'Для зв\'язку пишіть прямо в бот',
                'fr': 'Bot pour suivre les maux de tête, les médicaments et la pression\n'
                      'Pour le support, envoyez un message directement au bot',
                'es': 'Bot para el seguimiento de dolores de cabeza, medicamentos y presión\n'
                      'Para soporte, envíe un mensaje directamente al bot'
            }
            short_desc = short_desc.get(locale, short_desc['en'])
            assert len(short_desc) <= 120, f'Error: short description for {locale} is too long'
            result = await bot.request(
                'setMyShortDescription',
                data={
                    'short_description': short_desc,
                    'language_code': language_code
                },
            )
            if not result:
                logger.error(f'Error while setting bot short description for {locale}')

            async def set_long_description_after(delay_seconds: int, desc: str, language_code: str):
                await asyncio.sleep(delay_seconds)
                result = await bot.request(
                    'setMyDescription',
                    data={
                        'description': desc,
                        'language_code': language_code
                    },
                )
                if not result:
                    logger.error(f'Error while setting bot description for {language_code}')

            desc = {
                'ru': 'Этот бот предназначен для ведения дневника головных болей.\n'
                      'Он будет отслеживать, когда болела голова, какие медикаменты принимались, ваше давление, '
                      'а также спросит про возможные триггеры и проявлявшиеся симптомы.\n'
                      'Для связи и сообщениях об ошибках — пишите прямо в бота.',
                'en': 'This bot is intended for tracking headaches.\n'
                      'It will track when your head hurt, what medications were taken, your blood pressure, '
                      'and will also ask about possible triggers and symptoms.\n'
                      'For support and bug reports — message the bot directly.',
                'uk': 'Цей бот призначений для ведення щоденника головних болей.\n'
                      'Він буде відстежувати, коли боліла голова, які медикаменти приймалися, ваш тиск, '
                      'а також запитає про можливі тригери та проявлявшіся симптоми.\n'
                      'Для зв\'язку та повідомлень про помилки — пишіть прямо в бота.',
                'fr': 'Ce bot est destiné à suivre les maux de tête.\n'
                      'Il suivra quand votre tête vous faisait mal, quels médicaments ont été pris, votre tension artérielle, '
                      'et demandera également des informations sur les déclencheurs possibles et les symptômes.\n'
                      'Pour le support et les rapports de bogues — envoyez un message directement au bot.',
                'es': 'Este bot está destinado a rastrear dolores de cabeza.\n'
                      'Seguirá cuándo le dolía la cabeza, qué medicamentos se tomaron, su presión arterial, '
                      'y también preguntará sobre posibles desencadenantes y síntomas.\n'
                      'Para soporte y reportes de errores — envíe un mensaje directamente al bot.'
            }
            desc = desc.get(locale, desc['en'])
            assert len(desc) <= 512, f'Error: long description for {locale} is too long'
            delay = 20
            if sys.getsizeof(desc) >= 512:
                logger.warning(f'Long description for {locale} is too long, will be sent after delay')
                asyncio.create_task(set_long_description_after(delay, desc, language_code))
                delay += 20
            else:
                result = await bot.request(
                    'setMyDescription',
                    data={
                        'description': desc,
                        'language_code': language_code
                    },
                )
                if not result:
                    logger.error(f'Error while setting bot description for {locale}')
    except RetryAfter:
        logger.error('RetryAfter error while setting bot name')
