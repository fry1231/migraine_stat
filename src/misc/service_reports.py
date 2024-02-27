from src.bot import bot
from src.config import MY_TG_ID
from src.fsm_forms import available_fsm_states
from db.models import PainCase, DrugUse, Pressure, Drug
from db.redis.models import PydanticUser, EverydayReport
import db.redis.crud as redis_crud
import db.sql as sql


async def everyday_report(reset_old_one: bool = True) -> None:
    report: EverydayReport = await redis_crud.get_current_report()
    deleted_users: list[PydanticUser] = report.deleted_users

    # Get notification text about users joined during the day
    new_users_text = await notif_of_new_users() + '\n\n'
    new_users_text += f'{report.n_notified_users} users notified\n'

    # Count users with at least one added row in Pains table - they are active_users
    active_users = await sql.get_users(active=True)
    active_users_ids = [user.telegram_id for user in active_users]

    # Users who have something recorded within the last 31 days - superactive users
    n_superactive_users = await sql.get_users(super_active=True, return_count=True)

    # Users who have regular notification
    not_notifiable_users = await sql.get_users_where(notify_every=-1)
    n_users = await sql.get_users(return_count=True)
    n_notifiable_users = n_users - len(not_notifiable_users)

    # Who deleted?
    text_deleted = 'Deleted users:\n'
    user: PydanticUser
    for i, user in enumerate(deleted_users):
        username = '' if user.user_name is None else 't.me/' + user.user_name
        active = ''
        if any([user.n_paincases, user.n_druguses, user.n_pressures, user.n_medications]):
            active += f' ({user.n_paincases} pain, {user.n_druguses} druguses, {user.n_pressures} pressures, {user.n_medications} meds)'
        text_deleted += f'{i+1}. {user.first_name} {username} {active} deleted\n'
    text_deleted += '\n'

    # number of rows in Pain, DrugUse, Pressure, Drug tables
    n_pains = await sql.get_all_(PainCase, return_count=True)
    n_druguses = await sql.get_all_(DrugUse, return_count=True)
    n_pressures = await sql.get_all_(Pressure, return_count=True)
    n_medications = await sql.get_all_(Drug, return_count=True)

    stats = f'Pains: {report.n_pains} / {n_pains}\n' \
            f'DrugUses: {report.n_druguses} / {n_druguses}\n' \
            f'Pressures: {report.n_pressures} / {n_pressures}\n' \
            f'Drugs: {report.n_medications} / {n_medications}\n'

    text = f'{n_notifiable_users}/{n_users} users with notification\n' \
           f'{len(active_users)} active and {n_superactive_users} superactive users\n\n' \
           f'{text_deleted}' \
           f'{stats}'
    await bot.send_message(chat_id=MY_TG_ID, text=text)
    if reset_old_one:
        await redis_crud.init_everyday_report()
        await redis_crud.init_states(available_fsm_states)


async def notif_of_new_users() -> str:
    """
    Only once consume messages from the "new_users" queue
    Each message contains encoded User_Pydantic instance
        of a new user for the previous day

    Return text for notification on new users
    """
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

    current_report = await redis_crud.get_current_report()
    users_list: list[PydanticUser] = current_report.new_users

    # Construct notification text
    text = f'{len(users_list)} new users'
    if len(users_list) != 0:
        text += ':'
    user: PydanticUser
    for i, user in enumerate(users_list):
        telegram_id = user.telegram_id
        first_name = user.first_name
        last_name = user.last_name or ''
        user_name = user.user_name
        language = user.language
        text += f'\n{i+1}. ({telegram_id}) {first_name} {last_name} ({language})'
        if user_name:
            text += f't.me/{user_name}'
    return text
