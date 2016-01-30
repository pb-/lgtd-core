import os
import re
from collections import defaultdict
from json import loads

from tornado import ioloop, web

from ..lib.constants import APP_ID_LEN
from ..lib.db import SyncableDatabase

IS_VALID_APP_ID = re.compile('^[a-zA-Z0-9]{%d}$' % APP_ID_LEN).match
IS_VALID_TOKEN = re.compile('^[a-zA-Z0-9]{10}$').match


class AuthenticationError(Exception):
    pass


def validate_type(datum, type_):
    if not isinstance(datum, type_):
        raise ValueError


def validate_in(item, collection):
    if item not in collection:
        raise ValueError


def validate_app_id(app_id):
    validate_type(app_id, basestring)
    if not IS_VALID_APP_ID(app_id):
        raise ValueError


def validate_positive_int(datum):
    validate_type(datum, int)
    if datum < 0:
        raise ValueError


def parse_pull_input(encoded):
    json = loads(encoded)

    validate_in('offs', json)
    validate_type(json['offs'], dict)

    for app_id in json['offs']:
        validate_app_id(app_id)
        validate_positive_int(json['offs'][app_id])

    return json


def parse_push_input(encoded):
    json = loads(encoded)

    validate_in('data', json)
    validate_type(json['data'], dict)

    for app_id in json['data']:
        validate_app_id(app_id)
        validate_type(json['data'][app_id], list)
        if not len(json['data'][app_id]) == 2:
            raise ValueError

        validate_positive_int(json['data'][app_id][0])
        validate_type(json['data'][app_id][1], basestring)
        if not len(json['data'][app_id][1]):
            raise ValueError

    return json


def authenticate(auth_token):
    if not (IS_VALID_TOKEN(auth_token) and
            os.path.isdir(os.path.join('data', auth_token))):
        raise AuthenticationError


class BaseHandler(web.RequestHandler):
    def process(self):
        raise NotImplemented

    def post(self, auth_token):
        try:
            authenticate(auth_token)
            self.db = SyncableDatabase(os.path.join('data', auth_token))
            self.process()
        except AuthenticationError:
            self.send_error(401)


class PullHandler(BaseHandler):
    def process(self):
        local_offs = self.db.get_offsets()
        try:
            remote = parse_pull_input(self.request.body)
            remote_offs = defaultdict(int, remote['offs'])

            self.write({
                'offs': local_offs,
                'data': self.db.get_missing_data(local_offs, remote_offs),
            })
        except ValueError:
            self.send_error(400)


class PushHandler(BaseHandler):
    def process(self):
        try:
            remote = parse_push_input(self.request.body)
            local_offs = self.db.get_offsets()
            if not self.db.is_gapless(local_offs, remote['data']):
                self.send_error(400)
            else:
                self.db.insert_data(local_offs, remote['data'])
                self.write({})
        except ValueError:
            self.send_error(400)


def make_app():
    return web.Application([
        (r'/gtd/([0-9a-zA-Z]{10})/pull', PullHandler),
        (r'/gtd/([0-9a-zA-Z]{10})/push', PushHandler),
    ])


def run():
    app = make_app()
    app.listen(9002)
    ioloop.IOLoop.current().start()
