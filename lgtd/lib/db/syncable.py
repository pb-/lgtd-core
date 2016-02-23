import os

from .base import BaseDatabase


class Database(BaseDatabase):
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
