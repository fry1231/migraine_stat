from src.bot import bot


async def notify_me(text):
    await bot.send_message(358774905, text)
