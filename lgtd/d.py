import logging
import os
from argparse import ArgumentParser
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta
from getpass import getpass
from json import dumps, loads

import pyinotify
from tornado import ioloop, web
from tornado.websocket import WebSocketHandler

from .lib.commands import Command
from .lib.crypto import CommandCipher, hash_password
from .lib.db import ClientDatabase
from .lib.util import (ensure_data_dir, ensure_lock_file, get_data_dir,
                       get_local_config, get_lock_file)

logger = logging.getLogger(__name__)


class StateManager(object):
    def __init__(self, app_id, db, cipher):
        self.state = {
            'tag_order': ['inbox', 'todo', 'ref', 'someday', 'tickler'],
            'items': OrderedDict(),
        }
        self.offsets = defaultdict(int)
        self.app_id = app_id
        self.cipher = cipher
        self.db = db

    @staticmethod
    def _display_tag(tag, ref_date):
        if not tag:
            return 'inbox'

        if tag.startswith('$'):
            tag_date = tag[1:]
            return 'tickler' if tag_date > ref_date else 'inbox'

        return tag

    def notify(self):
        """
        Returns true if there are changes
        """
        with self.db.lock(True):
            offsets = self.db.get_offsets()
            if offsets == self.offsets:
                return False

            for line, app_id, offset in self.db.read_all(self.offsets):
                cmd = Command.parse(self.cipher.decrypt(line, app_id, offset))
                cmd.apply(self.state)
                logger.debug('executing: {}'.format(str(cmd)))

            self.offsets = offsets
            return True

    def push_commands(self, commands):
        with self.db.lock(), self.db.append(self.app_id) as f:
            for command in commands:
                line = self.cipher.encrypt(
                    command.encode('utf-8'), self.app_id, f.tell())
                f.write(line)

    def render_state(self, active_tag):
        today = str(date.today())
        counts = defaultdict(int)
        items = []

        if active_tag not in self.state['tag_order']:
            active_tag = 'inbox'

        for item_id, item in self.state['items'].iteritems():
            actual_tag = self._display_tag(item['tag'], today)
            counts[actual_tag] += 1
            if actual_tag == active_tag:
                data = {
                    'id': item_id,
                    'title': item['title'],
                }
                if item['tag'].startswith('$'):
                    data['scheduled'] = item['tag'][1:]

                items.append(data)

        tags = map(
            lambda tag: {'name': tag, 'count': counts[tag]},
            self.state['tag_order']
        )

        return {
            'tags': tags,
            'active_tag': self.state['tag_order'].index(active_tag),
            'items': items,
        }


class GTDSocketHandler(WebSocketHandler):
    def initialize(self, clients, state_manager):
        self.clients = clients
        self.state_manager = state_manager

    def check_origin(self, origin):
        return True

    def open(self):
        self.clients.append(self)
        logger.debug('client connected')

    def on_message(self, message):
        data = loads(message)
        logger.debug('message {}'.format(data))

        if data['msg'] == 'request_state':
            logger.debug('replying with state')
            state = self.state_manager.render_state(
                data['tag'].encode('utf-8'))
            self.write_message(dumps({'msg': 'state', 'state': state}))
        elif data['msg'] == 'push_commands':
            logger.debug('pushing some commands')
            self.state_manager.push_commands(data['cmds'])

    def notify(self):
        self.write_message('{"msg": "new_state"}')

    def on_close(self):
        self.clients.remove(self)
        logger.debug('client disconnected')


def change_callback(notifier):
    logger.debug('change?')
    if notifier.state_manager.notify():
        logger.debug('change - notifying clients')
        for client in notifier.clients:
            client.notify()


def delta_to_midnight():
    """
    Return a timedelta until next day five minutes past midnight.
    """
    now = datetime.now()
    dt = now + timedelta(days=1)
    midnight = dt.replace(hour=0, minute=5, second=0, microsecond=0)
    return midnight - now


def midnight_callback(ioloop, clients):
    """
    Make sure clients receive new state after the day rolls over (may affect
    inbox and tickler for scheduled items).
    """
    for client in clients:
        client.notify()

    schedule_midnight(ioloop, clients)


def schedule_midnight(ioloop, clients):
    ioloop.add_timeout(delta_to_midnight(), midnight_callback, ioloop, clients)


def parse_args():
    parser = ArgumentParser(description='local data service for lgtd')
    parser.add_argument(
        '-d', '--daemon', action='store_true', help='daemonize after asking '
        'for the encryption passphrase and starting to listen')
    return parser.parse_args()


def run_daemon(args, key, pipe_write):
    clients = []
    config = get_local_config()
    state_manager = StateManager(
        config['app_id'],
        ClientDatabase(get_data_dir(), get_lock_file()), CommandCipher(key))

    ensure_lock_file()
    ensure_data_dir()
    wm = pyinotify.WatchManager()
    notifier = pyinotify.TornadoAsyncNotifier(
        wm, ioloop.IOLoop.current(), change_callback, pyinotify.ProcessEvent())
    notifier.clients = clients
    notifier.state_manager = state_manager
    wm.add_watch(get_lock_file(), pyinotify.IN_CLOSE_WRITE)

    state_manager.notify()  # make sure initial state is prepared

    app = web.Application([
        (r'/gtd', GTDSocketHandler, {
            'clients': clients,
            'state_manager': state_manager}),
    ])
    app.listen(9001, address='127.0.0.1')
    logger.info('listening')

    if pipe_write:
        # notify parent proc that we are listening now
        os.close(pipe_write)

    schedule_midnight(ioloop.IOLoop.current(), clients)
    ioloop.IOLoop.current().start()


def run():
    args = parse_args()
    key = hash_password(getpass())

    if args.daemon:
        logger.setLevel(logging.INFO)
        handler = logging.handlers.SysLogHandler('/dev/log')
        handler.setFormatter(logging.Formatter('%(name)s %(message)s'))
        logger.addHandler(handler)

        pipe_read, pipe_write = os.pipe()
        pid = os.fork()
        if pid:
            os.close(pipe_write)
            os.read(pipe_read, 1)  # wait until we are listening
            return 0
        else:
            os.close(pipe_read)
    else:
        logging.basicConfig(level=logging.DEBUG)

    run_daemon(args, key, pipe_write if args.daemon else None)
