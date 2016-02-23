import os
from contextlib import contextmanager

from ..crypto import CommandCipher
from .base import BaseDatabase


class Database(BaseDatabase):
    """
    Database interface for actual data access.
    """
    @staticmethod
    def _read_line(f):
        offset = f.tell()
        line = f.readline()
        if not line:
            f.close()
            return None
        else:
            return (CommandCipher.extract_time(line), line, f, offset)

    @contextmanager
    def append(self, app_id):
        path = os.path.join(self.data_path, app_id)

        with open(path, 'ab') as f:
            yield f

    def read_all(self, start_offs):
        lines = []

        # read first line from each file
        for app_id in os.listdir(self.data_path):
            f = open(os.path.join(self.data_path, app_id), 'r')
            f.seek(start_offs[app_id])
            line = self._read_line(f)
            if line:
                lines.append(line + (app_id, ))

        while lines:
            lines.sort()
            (_, line, f, offset, app_id) = lines[0]
            yield line, app_id, offset
            del lines[0]

            line = self._read_line(f)
            if line:
                lines.insert(0, line + (app_id, ))
