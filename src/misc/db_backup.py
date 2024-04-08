import asyncio
import datetime
import subprocess
import time
import pathlib
import traceback
import yadisk

from src.config import logger, POSTGRES_USER, POSTGRES_PASS, PERSISTENT_DATA_DIR
from src.misc.utils import notify_me


def get_token():
    if pathlib.Path('/usr/persistent_data/yadisk_token.txt').exists():
        with open('/usr/persistent_data/yadisk_token.txt') as f:
            token = f.read()
        if token != '':
            return token
    return 'empty_token'


async def do_backup() -> bool:
    """
    Create a backup of the database and upload it to Yandex Disk
    Backup is created with pg_dump and saved as a .gz file
    Needs Yandex Disk token to be saved in /usr/persistent_data/yadisk_token.txt
    Token updates with /token command
    :return: True if backup was successful, False otherwise
    """
    t0 = time.time()
    logger.info('Starting backup')
    time_now = datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d_%H:%M:%S%z')
    filepath = PERSISTENT_DATA_DIR / f'{time_now}.migraine_backup'
    filepath = filepath.as_posix()
    # assert ' ' not in filepath, 'Spaces in filepath are not allowed'
    cmd = f'pg_dump --data-only --dbname=postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@migraine_db:5432/db_prod' \
          f' | gzip -c > {filepath}'
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(1)
    if p.returncode != 0:
        logger.error(err := f'Backup with pg_dump failed, exit code: {p.returncode}')
        await notify_me(err)
        return False
    logger.info(f'Created backup file {time_now}.migraine_backup in {time.time() - t0:.2f} sec')

    # Saving file to Yandex Disk
    token = get_token()
    client = yadisk.AsyncClient(token=token)
    prefix = 'Приложения/migrebot/'
    async with client:
        # Check if the token is valid
        if not await client.check_token():
            logger.error('Invalid Yandex Disk token')
            await notify_me('Please update Yandex Disk token, using /token command')
            return False
        try:
            # Upload backup (avoiding limited upload speed for archives)
            await client.upload(filepath, f"{prefix}{time_now}.migraine_backup")
            await client.rename(f"{prefix}{time_now}.migraine_backup", f"{time_now}.gz")

            # Deleting old backups (older than 180 days)
            async for file in await client.listdir(prefix):
                if file.name.endswith('.gz'):
                    date = datetime.datetime.strptime(file.name.split('.')[0], '%Y-%m-%d_%H:%M:%S%z')
                    if (datetime.datetime.now(tz=datetime.timezone.utc) - date).days > 180:
                        logger.info(f'Deleting old backup {file.name}')
                        await client.remove(file.path)
                        pathlib.Path(filepath).unlink()
            logger.info(f'Backup finished successfully in {time.time() - t0:.2f} sec')
            return True
        except Exception:
            logger.error(f'Error while doing backup\n{traceback.format_exc()}')
            return False
