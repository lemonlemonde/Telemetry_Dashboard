from queue import Queue, Empty, Full
import logging

class MetricQueue:
    """
    Queue with behavior:
    - maxsize 10
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
        try:
            self._queue.put_nowait(val)
        except Full:
            dropped = self._queue.get_nowait()
            self._queue.put_nowait(val)
            self._logger.warning(f'Queue ({self._name}) full. Dropped value: {dropped}.')
    
    def get(self):
        # return val or None if empty
        # non blocking
        try:
            return self._queue.get_nowait()
        except Empty:
            self._logger.warning(f'Queue ({self._name}) empty.')
            return None