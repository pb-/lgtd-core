import os
from collections import defaultdict
from contextlib import contextmanager
from fcntl import LOCK_EX, LOCK_UN, flock


class BaseDatabase(object):
    def __init__(self, data_path, lock_path=None):
        self.data_path = data_path
        self.lock_path = lock_path

    @contextmanager
    def lock(self, read_only=False):
        mode = 'r' if read_only else 'a'
        with open(self.lock_path, mode) as f:
            flock(f, LOCK_EX)
            yield
            flock(f, LOCK_UN)

    def get_offsets(self):
        app_ids = os.listdir(self.data_path)
        sizes = map(
            lambda app_id: (
                app_id, os.path.getsize(os.path.join(self.data_path, app_id))
            ), app_ids)

        return defaultdict(int, sizes)
