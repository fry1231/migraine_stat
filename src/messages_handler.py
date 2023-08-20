from aio_pika import Message, connect_robust, DeliveryMode
from aio_pika.abc import AbstractIncomingMessage, AbstractChannel
from contextlib import asynccontextmanager
from os import getenv
from db.models import NewUser
import orjson as json


# @asynccontextmanager
# async def rabbit_channel() -> AbstractChannel:
#     """
#     Establishes a connection to the RabbitMQ server using
#         the credentials provided as environment variables.
#     Creates a channel within the connection
#
#     Yields a channel (durable)
#     Notifies and raises on error
#     """
#     user = getenv('RABBITMQ_USER')
#     passw = getenv('RABBITMQ_PASS')
#     host = getenv('RABBITMQ_HOST')
#     connection = await connect_robust(f"amqp://{user}:{passw}@{host}/")
#     try:
#         async with connection:
#             channel = await connection.channel()
#             yield channel
#     except Exception:
#         # await notify_me('Error while dealing with RabbitMQ:\n' + traceback.format_exc())
#         raise
#     finally:
#         await connection.close()


async def postpone_new_user_notif(user: NewUser) -> None:
    """
    Sends a message to the new_users queue for being
        processed later on regular everyday notification
    """
    # queue_name = 'new_users'
    # async with rabbit_channel() as channel:
    #     await channel.declare_queue(queue_name, durable=True)
    #     await channel.default_exchange.publish(
    #         Message(user.json().encode(), delivery_mode=DeliveryMode.PERSISTENT),
    #         routing_key=queue_name
    #     )
    with open('/usr/persistent_data/new_users.json', 'a') as file:
        file.write(json.dumps(user.dict()).decode('utf8') + '\n')


async def notif_of_new_users() -> str:
    """
    Only once consume messages from the "new_users" queue
    Each message contains encoded User_Pydantic instance
        of a new user for the previous day

    Return text for notification on new users
    """
    users_list: list[NewUser] = []
    # queue_name = 'new_users'
    # async with rabbit_channel() as channel:
    #     queue = await channel.declare_queue(queue_name, durable=True)
    #     n_messages = queue.declaration_result.message_count
    #     i = 0
    #     if n_messages == 0:
    #         return "No new users today"
    #     async with queue.iterator() as queue_iter:
    #         async for message in queue_iter:
    #             i += 1
    #             async with message.process():  # automatically ack the message
    #                 users_list.append(NewUser.parse_raw(message.body))
    #                 if i == n_messages:
    #                     break

    try:
        with open('/usr/persistent_data/new_users.json', 'r', encoding='utf8') as file:
            users_list = [NewUser(**json.loads(line)) for line in file]
    except FileNotFoundError:
        pass

    # Emptying file for the next day users
    open('/usr/persistent_data/new_users.json', 'w').close()

    # Construct notification text
    text = f'{len(users_list)} new users'
    if len(users_list) != 0:
        text += ':'
    for user in users_list:
        first_name = user.first_name
        last_name = user.last_name or ''
        user_name = user.user_name
        text += f'\n{first_name} {last_name} '
        if user_name:
            text += f't.me/{user_name}'
    return text
