# import matplotlib.pyplot as plt
# import numpy as np
# import six
from src.bot import bot
from xlsxwriter import Workbook
import io
from os import getenv


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
