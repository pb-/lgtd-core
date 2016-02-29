import unittest
from datetime import datetime, timedelta

from ..bucket import LeakyBucket


class NowMock(object):
    def __init__(self):
        self.dt = datetime(2016, 1, 1)

    def __call__(self):
        return self.dt

    def modify(self, second, microsecond=0):
        self.dt = self.dt.replace(second=second, microsecond=microsecond)


class BucketTestCase(unittest.TestCase):
    def test_trivial(self):
        bucket = LeakyBucket(timedelta(seconds=1), 3, NowMock())
        for _ in xrange(3):
            bucket.consume()

        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

    def test_simple_drop(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 1, now)
        bucket.consume()

        now.modify(1)
        bucket.consume()

        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

    def test_continuous(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 1, now)

        for s in xrange(60):
            now.modify(s)
            bucket.consume()

            with self.assertRaises(LeakyBucket.Insufficient):
                bucket.consume()

    def test_continuous_partial(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 1, now)

        for s in xrange(60):
            now.modify(s, 123456)
            bucket.consume()

            with self.assertRaises(LeakyBucket.Insufficient):
                bucket.consume()

    def test_long_delay(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 2, now)
        bucket.consume()
        bucket.consume()

        now.modify(59)
        bucket.consume()
        bucket.consume()

        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

    def test_long_initial_delay(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 3, now)
        now.modify(59)

        for _ in xrange(3):
            bucket.consume()

        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

    def test_partial(self):
        now = NowMock()
        bucket = LeakyBucket(timedelta(seconds=1), 1, now)
        bucket.consume()

        now.modify(0, 200000)
        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

        now.modify(0, 999000)
        with self.assertRaises(LeakyBucket.Insufficient):
            bucket.consume()

        now.modify(1)
        bucket.consume()
