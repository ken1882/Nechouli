import time
import asyncio
from datetime import datetime, timedelta
from functools import wraps

def timer(function):
    """
    Decorator that measures and prints the execution time of the decorated function.
    Supports both synchronous and asynchronous functions.
    """
    if asyncio.iscoroutinefunction(function):
        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            t0 = time.time()
            result = await function(*args, **kwargs)
            t1 = time.time()
            print(f'{function.__name__}: {round(t1 - t0, 10)} s')
            return result
        return async_wrapper
    else:
        @wraps(function)
        def sync_wrapper(*args, **kwargs):
            t0 = time.time()
            result = function(*args, **kwargs)
            t1 = time.time()
            print(f'{function.__name__}: {round(t1 - t0, 10)} s')
            return result
        return sync_wrapper


def future_time(string):
    """
    Args:
        string (str): Such as "14:59".
    Returns:
        datetime: Time with given hour, minute in the future.
    """
    hour, minute = [int(x) for x in string.split(':')]
    future = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    future = future + timedelta(days=1) if future < datetime.now() else future
    return future


def past_time(string):
    """
    Args:
        string (str): Such as "14:59".
    Returns:
        datetime: Time with given hour, minute in the past.
    """
    hour, minute = [int(x) for x in string.split(':')]
    past = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = past - timedelta(days=1) if past > datetime.now() else past
    return past


def future_time_range(string):
    """
    Args:
        string (str): Such as "23:30-06:30".
    Returns:
        tuple(datetime, datetime): (time start, time end).
    """
    start, end = [future_time(s) for s in string.split('-')]
    if start > end:
        start = start - timedelta(days=1)
    return start, end


def time_range_active(time_range):
    """
    Args:
        time_range (tuple(datetime, datetime)): (time start, time end).
    Returns:
        bool: True if current time is within the range.
    """
    return time_range[0] < datetime.now() < time_range[1]


class Timer:
    def __init__(self, limit, count=0):
        """
        Args:
            limit (int, float): Timer limit in seconds.
            count (int): Confirmation count before timer is considered reached.
        """
        self.limit = limit
        self.count = count
        self._current = 0
        self._reach_count = count

    def start(self):
        """Start the timer if not already started."""
        if not self.started():
            self._current = time.time()
            self._reach_count = 0
        return self

    def started(self):
        """Return True if the timer has been started."""
        return bool(self._current)

    def current(self):
        """
        Returns:
            float: Elapsed time in seconds.
        """
        if self.started():
            return time.time() - self._current
        else:
            return 0.

    def set_current(self, current, count=0):
        """Set the timer's current elapsed time and counter."""
        self._current = time.time() - current
        self._reach_count = count

    def reached(self):
        """
        Increments the internal counter and checks if the timer has exceeded the limit.
        Returns:
            bool: True if the time limit is reached and counter condition is met.
        """
        self._reach_count += 1
        return time.time() - self._current > self.limit and self._reach_count > self.count

    def reset(self):
        """Reset the timer."""
        self._current = time.time()
        self._reach_count = 0
        return self

    def clear(self):
        """Clear the timer."""
        self._current = 0
        self._reach_count = self.count
        return self

    def reached_and_reset(self):
        """
        Check if the timer is reached and then reset it.
        Returns:
            bool: True if timer was reached, False otherwise.
        """
        if self.reached():
            self.reset()
            return True
        else:
            return False

    def wait(self):
        """
        Wait until the timer reaches its limit.
        """
        diff = self._current + self.limit - time.time()
        if diff > 0:
            time.sleep(diff)

    def show(self):
        from module.logger import logger
        logger.info(str(self))

    def __str__(self):
        return f'Timer(limit={round(self.current(), 3)}/{self.limit}, count={self._reach_count}/{self.count})'

    __repr__ = __str__
