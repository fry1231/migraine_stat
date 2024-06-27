import logging
import aioredis
import asyncio
from db.redis.models import LogUpdate


class RedisLogHandler(logging.Handler):
    """
    Custom logging handler that pushes log records to a Redis list.
    Along with pushing log record, sends a message to 'channel:logs' to reflect the changes
    """
    def __init__(self,
                 redis_conn: aioredis.Redis,
                 key: str,
                 max_len: int):
        super().__init__()
        self.key = key
        self.redis_conn = redis_conn
        self.max_len = max_len
        self.loop = None
        self.incr_value = -1

    def emit(self, record):
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._async_emit(record))

    async def _async_emit(self, record):
        log_entry = self.format(record)
        if isinstance(log_entry, str):
            if '_client.py:1758' in log_entry:   # Skip yadisk entries
                return
        await self.redis_conn.lpush(self.key, log_entry.encode('utf-8'))
        await self.redis_conn.ltrim(self.key, 0, self.max_len - 1)
        self.incr_value += 1
        log_update = LogUpdate(log_record=log_entry, log_incr_value=self.incr_value)
        await self.redis_conn.publish('channel:logs', log_update.json())
        await self.redis_conn.set('log_incr_value', self.incr_value)
