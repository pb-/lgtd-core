from datetime import datetime, timedelta


class LeakyBucket(object):
    class Empty(Exception):
        pass

    def __init__(self, refill_interval, capacity, now_func=datetime.now):
        self.capacity = capacity
        self.now = now_func
        self.refill_interval_sec = refill_interval.total_seconds()

        self.fill_level = self.capacity
        self.last_fill = self.now()

    def consume(self):
        now = self.now()
        drops = (now - self.last_fill).total_seconds() / \
            self.refill_interval_sec
        self.fill_level = min(self.fill_level + int(drops), self.capacity)

        partial_drop = drops - int(drops)
        self.last_fill = now - timedelta(
            seconds=partial_drop * self.refill_interval_sec)

        if not self.fill_level:
            raise self.Empty

        self.fill_level -= 1
