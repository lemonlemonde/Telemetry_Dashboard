from queue import Queue, Empty, Full
import logging

from datetime import datetime, timezone

class MetricQueue:
    """
    Queue with behavior:
    - maxsize 10
    - queue of tuples (val, timestamp)
    - string timestamp (datetime format, utc timezone) is auto appended during insertion (put())
    - if queue full:
        queue.put(val) discards oldest value at front of queue
        and adds newest value `val`
    - if queue empty:
        queue.get() handles Empty exception and returns None
    """
    
    def __init__(self, name,):
        self._queue = Queue(maxsize=10)
        self._name = name
        self._logger = logging.getLogger(self.__class__.__name__)
        
    def put(self, val) -> None:
        # throw away oldest val if queue full
        now_time = datetime.now(timezone.utc)
        try:
            self._queue.put_nowait((val, str(now_time)))
        except Full:
            dropped, timestamp = self._queue.get_nowait()
            self._queue.put_nowait((val, str(now_time)))
            self._logger.warning(f'Queue ({self._name}) full. Dropped old value: [{dropped}] of timestamp [{timestamp}]')
    
    def get(self):
        # return val or None if empty
        # non blocking
        try:
            return self._queue.get_nowait()
        except Empty:
            self._logger.warning(f'Queue ({self._name}) empty.')
            return None
        
    def get_len(self):
        # qsize() is approximate number of things in the queue
        # unreliable for multithreading bc it doesn't obtain a lock
        return self._queue.qsize()