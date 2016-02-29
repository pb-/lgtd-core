from datetime import datetime


class LeakyBucket(object):
    class Insufficient(Exception):
        pass

    def __init__(self, refill_interval, capacity, now_func=datetime.now):
        self.capacity = capacity
        self.now = now_func
        self.refill_interval_sec = refill_interval.total_seconds()

        self.fill_level = self.capacity
        self.last_fill = self.now()

    def consume(self, amount=1):
        now = self.now()
        drops = (now - self.last_fill).total_seconds() / \
            self.refill_interval_sec
        self.fill_level = min(self.fill_level + drops, self.capacity)
        self.last_fill = now

        remaining = self.fill_level - amount
        if remaining < 0:
            raise self.Insufficient

        self.fill_level = remaining
