import os
from collections import defaultdict
from fcntl import flock, LOCK_EX, LOCK_UN
from contextlib import contextmanager

from .crypto import CommandCipher


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
        app_ids = os.listdir(self.data_path)
        sizes = map(
            lambda app_id: (
                app_id, os.path.getsize(os.path.join(self.data_path, app_id))
            ), app_ids)

        return defaultdict(int, sizes)


class SyncableDatabase(BaseDatabase):
    """
    Database interface for sync logic.
    """
    def _get_data(self, app_id, offset):
        with open(os.path.join(self.data_path, app_id), 'rb') as f:
            f.seek(offset)
            return f.read()

    def _put_data(self, app_id, offset, data):
        path = os.path.join(self.data_path, app_id)
        mode = 'rb+' if offset else 'ab'

        with open(path, mode) as f:
            f.seek(offset)
            f.write(data)

    def get_missing_data(self, local_offs, remote_offs):
        data = {}

        for app_id, local_off in local_offs.iteritems():
            remote_off = remote_offs[app_id]
            if local_off > remote_off:
                missing_data = self._get_data(app_id, remote_off)
                data[app_id] = [remote_off, missing_data]

        return data

    def insert_data(self, local_offs, remote_data):
        for app_id, (remote_off, data) in remote_data.iteritems():
            local_off = local_offs[app_id]
            overlap = local_off - remote_off
            self._put_data(app_id, local_off, data[overlap:])

    @staticmethod
    def is_gapless(local_offs, remote_data):
        for app_id, (remote_off, _) in remote_data.iteritems():
            if remote_off > local_offs[app_id]:
                return False

        return True


class ClientDatabase(BaseDatabase):
    """
    Database interface for actual data access.
    """
    @staticmethod
    def _read_line(f):
        line = f.readline()
        if not line:
            f.close()
            return None
        else:
            return (CommandCipher.extract_time(line), line, f)

    def append_data(self, app_id, data):
        path = os.path.join(self.data_path, app_id)

        with open(path, 'ab') as f:
            f.write(data)

    def read_all(self, start_offs):
        lines = []

        # read first line from each file
        for app_id in os.listdir(self.data_path):
            f = open(os.path.join(self.data_path, app_id), 'r')
            f.seek(start_offs[app_id])
            line = self._read_line(f)
            if line:
                lines.append(line)

        while lines:
            lines.sort()
            (_, line, f) = lines[0]
            yield line
            del lines[0]

            line = self._read_line(f)
            if line:
                lines.insert(0, line)
