import pyinotify
from json import loads, dumps
from collections import OrderedDict, defaultdict
from tornado import ioloop, web
from tornado.websocket import WebSocketHandler

from .lib.util import ensure_lock_file, get_lock_file


class StateManager(object):
    def __init__(self):
        self.state = {
            'tag_order': ['inbox', 'todo', 'someday', 'tickler', 'ref'],
            'items': OrderedDict(),
        }
        self.offsets = defaultdict(int)

    @staticmethod
    def _display_tag(tag, for_date):
        pass

    def notify(self):
        """
        Returns true if there are changes
        """
        return True

    def render_state(self, active_tag):
        mock_model = {
            'tags': [
                {'name': 'inbox', 'count': 3},
                {'name': 'todo', 'count': 0},
                {'name': 'someday', 'count': 4},
                {'name': 'tickler', 'count': 0},
                {'name': 'ref', 'count': 19},
            ],
            'active_tag': 0,
            'items': [
                {'id': 'ab0', 'title': 'some stuff'},
                {'id': 'ab1', 'title': 'old stuff', 'scheduled': '2015-12-04'},
                {'id': 'ab2', 'title': 'really important things'},
            ]
        }

        return mock_model


class GTDSocketHandler(WebSocketHandler):
    def initialize(self, clients, state_manager):
        self.clients = clients
        self.state_manager = state_manager

    def open(self):
        self.clients.append(self)
        print("WebSocket opened")

    def on_message(self, message):
        data = loads(message)
        print('got msg {}'.format(data))

        if data['msg'] == 'request_state':
            print('replying with state')
            state = self.state_manager.render_state(data['tag'])
            self.write_message(dumps({'msg': 'state', 'state': state}))

    def notify(self):
        self.write_message('{"msg": "new_state"}')

    def on_close(self):
        self.clients.remove(self)
        print("WebSocket closed")


def callback(notifier):
    if notifier.state_manager.notify():
        for client in notifier.clients:
            client.notify()


def run():
    clients = []
    state_manager = StateManager()

    ensure_lock_file()
    wm = pyinotify.WatchManager()
    notifier = pyinotify.TornadoAsyncNotifier(
        wm, ioloop.IOLoop.current(), callback, pyinotify.ProcessEvent())
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
    ioloop.IOLoop.current().start()
