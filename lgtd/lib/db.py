from fcntl import flock, LOCK_EX, LOCK_UN
from contextlib import contextmanager


class BaseDatabase(object):
    def __init__(self, data_path, lock_path=None):
        self.data_path = data_path
        self.lock_path = lock_path

    @contextmanager
    def lock(self):
        with open(self.lock_path, 'a') as f:
            flock(f, LOCK_EX)
            yield
            flock(f, LOCK_UN)

    def get_offsets(self):
        pass


class SyncableDatabase(BaseDatabase):
    """
    Database interface for sync logic.
    """
    def _get_data(app_id, offset):
        pass

    def _put_data(app_id, offset, data):
        pass

    def get_missing_data(local_offs, remote_offs):
        pass

    def insert_data(local_offs, remote_data):
        pass


class ClientDatabase(BaseDatabase):
    """
    Database interface for actual data access.
    """
    def append_data(app_id, data):
        pass

    def read_all(start_offs):
        pass
