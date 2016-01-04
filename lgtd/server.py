import re
import sqlite3

from base64 import decodestring
from json import loads
from tornado import ioloop, web


IS_VALID_APP_ID = re.compile('^[a-zA-Z0-9]{2}$').match


class AuthenticationError(Exception):
    pass


def parse_pull_input(data):
    data = loads(data)

    if 'revs' not in data:
        raise ValueError

    for app_id in data['revs']:
        if not IS_VALID_APP_ID(app_id):
            raise ValueError
        if not isinstance(data['revs'][app_id], int):
            raise ValueError
        if data['revs'][app_id] < 1:
            raise ValueError

    return data


def parse_push_input(data):
    data = loads(data)

    if 'cmds' not in data:
        raise ValueError
    if not isinstance(data['cmds'], list):
        raise ValueError
    for cmd in data['cmds']:
        if not isinstance(cmd, list):
            raise ValueError
        if not len(cmd) == 5:
            raise ValueError
        for i in (0, 2, 3, 4):
            if not isinstance(cmd[i], basestring):
                raise ValueError
        if not isinstance(cmd[1], int):
            raise ValueError
        if cmd[1] < 1:
            raise ValueError
        if not IS_VALID_APP_ID(cmd[0]):
            raise ValueError

    return data


def authenticate(cursor, auth_header):
    if auth_header is None or not auth_header.startswith('Basic '):
        raise AuthenticationError

    decoded = decodestring(auth_header[6:])  # data past 'Basic '
    user, password = decoded.split(':', 2)
    cursor.execute('''
        SELECT
            id
        FROM
            users
        WHERE
            name = ? AND password = ?
    ''', (user, password))
    row = cursor.fetchone()

    if row is None:
        raise AuthenticationError

    return row['id']


def get_local_revs(cursor, user_id):
    cursor.execute('''
        SELECT
            app_id, MAX(rev) AS rev
        FROM
            commands
        WHERE
            user_id = ?
        GROUP BY
            app_id
    ''', (user_id, ))

    return {row['app_id']: row['rev'] for row in cursor}


def get_missing_cmds(cursor, user_id, remote_revs):
    params = [user_id]
    for app_id, rev in remote_revs.items():
        params += [app_id, rev]

    rev_filter = ' AND NOT (app_id = ? AND rev <= ?)' * len(remote_revs)
    cursor.execute('''
        SELECT
            app_id, rev, iv, mac, cmd
        FROM
            commands
        WHERE
            user_id = ? {}
    '''.format(rev_filter), params)

    return map(list, cursor.fetchall())


def insert_commands(cursor, user_id, commands):
    inserts = map(lambda l: [user_id] + l, commands)
    cursor.executemany('''
        INSERT OR IGNORE INTO
            commands
        VALUES
            (?, ?, ?, ?, ?, ?)
    ''', inserts)


class BaseHandler(web.RequestHandler):
    def initialize(self, db):
        self.db = db

    def process(self, cursor, user_id):
        raise NotImplemented

    def post(self):
        cursor = self.db.cursor()

        try:
            user_id = authenticate(
                cursor, self.request.headers.get('Authorization'))
            self.process(cursor, user_id)
        except AuthenticationError:
            self.send_error(401)

        cursor.close()
        self.db.commit()


class PullHandler(BaseHandler):
    def process(self, cursor, user_id):
        local_revs = get_local_revs(cursor, user_id)
        try:
            remote = parse_pull_input(self.request.body)
            self.write({
                'revs': local_revs,
                'cmds': get_missing_cmds(cursor, user_id, remote['revs']),
            })
        except ValueError:
            self.send_error(400)


class PushHandler(BaseHandler):
    def process(self, cursor, user_id):
        try:
            data = parse_push_input(self.request.body)
            insert_commands(cursor, user_id, data['cmds'])
            self.write({})
        except ValueError:
            self.send_error(400)


def make_app():
    db = sqlite3.connect('data.db')
    db.row_factory = sqlite3.Row

    return web.Application([
        (r"/pull", PullHandler, {'db': db}),
        (r"/push", PushHandler, {'db': db}),
    ])


def run():
    app = make_app()
    app.listen(4711)
    ioloop.IOLoop.current().start()
