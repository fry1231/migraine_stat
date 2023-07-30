# import matplotlib.pyplot as plt
# import numpy as np
# import six
import asyncio
from db import models, crud
from typing import List
from src.routes import regular_report
from src.bot import bot
from aiogram.utils.exceptions import BotBlocked, UserDeactivated, NetworkError
from xlsxwriter import Workbook
from src.messages_handler import notif_of_new_users
from datetime import datetime
import traceback
import io
from os import getenv


# Schedule notification task
async def notify_users():
    """
    Ask if there was a headache during missing period, defined in notify_every attr
    Notify daily about new users
    """
    users: List[models.User] = await crud.get_users()
    t = datetime.today()
    time_notified = datetime.now()
    users_id_w_notif = []
    n_notifyable_users = 0
    for user in users:
        notification_period_days = user.notify_every
        if notification_period_days == -1:  # If user did not specify it yet
            continue
        n_notifyable_users += 1
        notification_period_minutes = notification_period_days * 24 * 60
        dt = (t - user.last_notified).total_seconds() / 60
        if dt >= notification_period_minutes - 15:
            try:
                await regular_report(user_id=user.telegram_id, missing_days=notification_period_days)
                users_id_w_notif.append(user.telegram_id)
            except (BotBlocked, UserDeactivated):
                if crud.delete_user(user.telegram_id):
                    await notify_me(f'User {user.telegram_id} ({user.user_name} / {user.first_name}) deleted')
                else:
                    await notify_me(f'Error while deleting user {user.telegram_id} ({user.user_name} / {user.first_name})')
            except NetworkError:
                await notify_me(f'User {user.telegram_id} Network Error')
        await asyncio.sleep(1/30)   # As Telegram does not allow more than 30 messages/sec
    new_users_text = await notif_of_new_users()
    await notify_me(new_users_text)
    await notify_me(
        f'{len(users_id_w_notif)} users notified\n'
        f'Will change last notified on {time_notified}'
    )

    try:
        await crud.batch_change_last_notified(users_id_w_notif)
    except Exception:
        await notify_me('Error while executing batch_change_last_notified, fallback to the old version')
        await notify_me(traceback.format_exc())
        for user_id in users_id_w_notif:
            await crud.change_last_notified(user_id, time_notified)

    # Count users with at least one added row in Pains table
    active_users = set()
    pains: List[models.PainCase] = await crud.get_pains()
    for pain in pains:
        active_users.add(pain.owner_id)

    n_active = len(active_users.intersection(users_id_w_notif))
    n_deleted = len(active_users - set(users_id_w_notif))

    ex_time = (datetime.now() - time_notified).total_seconds()
    await notify_me(
        f'{n_notifyable_users}/{len(users)} users with notification\n'
        f'{n_active} active and {n_deleted} deleted after being active users\n'
        f'{len(pains)} rows in Pains table\n\n'
        f'Execution time = {ex_time // 60} min {ex_time % 60} sec'
    )


async def notify_me(text):
    my_tg_id = int(getenv('MY_TG_ID'))
    if len(text) > 4096:
        for pos in range(0, len(text), 4096):
            await bot.send_message(my_tg_id, text[pos:pos + 4096])
    else:
        await bot.send_message(my_tg_id, text)


# def render_mpl_table(data, col_width=3.0, row_height=0.625, font_size=14,
#                      header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
#                      bbox=[0, 0, 1, 1], header_columns=0,
#                      ax=None, **kwargs):
#     """
#     Renders an image with table from given data
#     """
#     if ax is None:
#         size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
#         fig, ax = plt.subplots(figsize=size)
#         ax.axis('off')
#
#     mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)
#
#     mpl_table.auto_set_font_size(False)
#     mpl_table.set_fontsize(font_size)
#
#     for k, cell in six.iteritems(mpl_table._cells):
#         cell.set_edgecolor(edge_color)
#         if k[0] == 0 or k[1] < header_columns:
#             cell.set_text_props(weight='bold', color='w')
#             cell.set_facecolor(header_color)
#         else:
#             cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
#     return ax.get_figure(), ax


def write_xlsx(buf: io.BytesIO, data: list[dict]) -> None:
    """
    Writes an xlsx file in buffer 'buf' from the given data.
    Modifies buffer inplace

    :arg data - list of dicts with column names as keys

    """
    wb = Workbook(buf)
    ws = wb.add_worksheet()

    ordered_list = list(data[0].keys())

    # Filling header
    first_row = 0
    for header in ordered_list:
        col = ordered_list.index(header)
        ws.write(first_row, col, header)

    # Filling data
    row = 1
    for el in data:
        for _key, _value in el.items():
            col = ordered_list.index(_key)
            ws.write(row, col, _value)
        row += 1
    wb.close()
    buf.seek(0)
