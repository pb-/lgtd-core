import os
import re
from collections import defaultdict
from json import loads

from tornado import ioloop, web

IS_VALID_APP_ID = re.compile('^[a-zA-Z0-9]{2}$').match
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


def is_gapless(local_offs, remote_data):
    for app_id, (remote_off, _) in remote_data.iteritems():
        if remote_off > local_offs[app_id]:
            return False

    return True


def authenticate(auth_token):
    if not (IS_VALID_TOKEN(auth_token) and
            os.path.isdir(os.path.join('data', auth_token))):
        raise AuthenticationError


def get_local_offs(auth_token):
    data_dir = os.path.join('data', auth_token)
    app_ids = os.listdir(data_dir)
    sizes = map(
        lambda app_id: (
            app_id, os.path.getsize(os.path.join(data_dir, app_id))
        ), app_ids)

    return defaultdict(int, sizes)


def get_data(auth_token, app_id, offset):
    with open(os.path.join('data', auth_token, app_id), 'rb') as f:
        if offset > 0:
            f.seek(offset)
        return f.read()


def put_data(auth_token, app_id, offset, data):
    path = os.path.join('data', auth_token, app_id)

    # make sure file exists in a non-invasive way
    with open(path, 'a') as f:
        pass

    with open(path, 'rb+') as f:
        f.seek(offset)
        f.write(data)


def get_missing_data(auth_token, local_offs, remote_offs):
    data = {}

    for app_id, local_off in local_offs.iteritems():
        remote_off = remote_offs[app_id]
        if local_off > remote_off:
            missing_data = get_data(auth_token, app_id, remote_off)
            data[app_id] = [remote_off, missing_data]

    return data


def insert_data(auth_token, local_offs, remote_data):
    for app_id, (remote_off, data) in remote_data.iteritems():
        local_off = local_offs[app_id]
        overlap = local_off - remote_off
        put_data(auth_token, app_id, local_off, data[overlap:])


class BaseHandler(web.RequestHandler):
    def process(self):
        raise NotImplemented

    def post(self, auth_token):
        try:
            authenticate(auth_token)
            self.auth_token = auth_token
            self.process()
        except AuthenticationError:
            self.send_error(401)


class PullHandler(BaseHandler):
    def process(self):
        local_offs = get_local_offs(self.auth_token)
        try:
            remote = parse_pull_input(self.request.body)
            remote_offs = defaultdict(int, remote['offs'])

            self.write({
                'offs': local_offs,
                'data': get_missing_data(
                    self.auth_token, local_offs, remote_offs),
            })
        except ValueError:
            self.send_error(400)


class PushHandler(BaseHandler):
    def process(self):
        try:
            remote = parse_push_input(self.request.body)
            local_offs = get_local_offs(self.auth_token)
            if not is_gapless(local_offs, remote['data']):
                self.send_error(400)
            else:
                insert_data(self.auth_token, local_offs, remote['data'])
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
    app.listen(4711)
    ioloop.IOLoop.current().start()
