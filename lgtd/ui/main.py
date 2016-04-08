import curses
import hmac
import logging
import os
import sys
from argparse import ArgumentParser
from json import dumps, loads
from locale import LC_ALL, setlocale
from select import error as select_error
from select import select
from threading import Thread

from websocket import WebSocketApp

from .state import Context, Input
from ..lib.util import get_local_config


class ModelStateAdapter(Thread):
    msg_size_len = 10
    msg_size_fmt = '{:0%d}' % msg_size_len

    def __init__(self, key, port):
        super(ModelStateAdapter, self).__init__()
        self.daemon = True
        self.key = key
        self.port = port
        self.read_fd, self.write_fd = os.pipe()

    def _send(self, msg):
        os.write(self.write_fd, self.msg_size_fmt.format(len(msg)))
        os.write(self.write_fd, msg)

    def stop(self):
        self.socket.close()

    def recv(self):
        msg_size = int(os.read(self.read_fd, self.msg_size_len))
        return loads(os.read(self.read_fd, msg_size))

    def authenticate(self, key, nonce):
        logging.debug('authenticating...')
        mac = hmac.new(str(key), str(nonce)).digest().encode('hex')
        self.socket.send(dumps({
            'msg': 'auth_response',
            'mac': mac,
        }))

    def request_state(self, active_tag):
        logging.debug('requesting state...')
        self.socket.send(dumps({
            'msg': 'request_state',
            'tag': active_tag,
        }))

    def push_commands(self, cmds):
        logging.debug('pushing commands...')
        self.socket.send(dumps({
            'msg': 'push_commands',
            'cmds': map(str, cmds),
        }))

    def _on_message(self, socket, message):
        self._send(message)

    def run(self):
        self.socket = WebSocketApp(
            'ws://127.0.0.1:{}/gtd'.format(self.port),
            on_message=self._on_message)

        self.socket.run_forever()


class WindowTooSmallError(Exception):
    pass


def content_height(scr):
    # usable height minus: title bar, pad, pad, status bar (4)
    ymax, _ = scr.getmaxyx()
    return ymax - 4


def render(scr, context):
    scr.erase()
    (y, x) = scr.getmaxyx()
    col = curses.color_pair(1)
    scr.addstr(0, 0, ' ' * x, col)
    scr.addstr(0, 2, 'GTD', col)

    height = content_height(scr)
    if height < 1:
        raise WindowTooSmallError()

    for i, tag in enumerate(context.model['tags']):
        if i < context.vars['scroll_offset_tags']:
            continue
        ii = i - context.vars['scroll_offset_tags']
        if not ii < height:
            break

        scr.addnstr(ii+2, 3, tag['name'].encode('utf-8'), 9)
        if tag['count']:
            scr.addstr(' ({})'.format(tag['count']))
        if i == context.vars['active_tag']:
            scr.addstr(ii+2, 1, '|')

    for i, item in enumerate(context.model['items']):
        if i < context.vars['scroll_offset_items']:
            continue
        ii = i - context.vars['scroll_offset_items']
        if not ii < height:
            break

        scr.addstr(ii+2, 20, item['title'].encode('utf-8'))
        if 'scheduled' in item:
            scr.addstr('  [{}]'.format(
                item['scheduled']), curses.color_pair(2))
        if i == context.vars['active_item']:
            scr.addstr(ii+2, 18, '>')

    if isinstance(context.state, Input):
        curses.curs_set(1)
        scr.addstr(y-1, 2, '> ' + context.state.input_buffer)
        scr.move(y-1, 4 + len(
            context.state.input_buffer.decode('utf-8', 'ignore')))
    else:
        curses.curs_set(0)

    scr.refresh()


def main(scr, config, args):
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.noecho()
    curses.cbreak()
    scr.keypad(1)

    state_adapter = ModelStateAdapter(config['local_auth'], args.port)
    state_adapter.start()

    model_state = {
        'tags': [{'name': 'inbox', 'count': 0}],
        'items': [],
    }

    context = Context(model_state, state_adapter)
    context.vars['content_height'] = content_height(scr)

    while True:
        render(scr, context)

        try:
            selected, _, _ = select(
                [sys.stdin, context.adapter.read_fd], [], [])
        except select_error:
            curses.resizeterm(*scr.getmaxyx())
            scr.refresh()
            selected = []
        if sys.stdin in selected:
            key = scr.getch()
            consumed = context.handle_input(key)
            if not consumed:
                if key == ord('q'):
                    break
        if context.adapter.read_fd in selected:
            context.handle_data(context.adapter.recv())


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--port', '-p', type=int, default=9001, help=''
                        'port to connect to')

    return parser.parse_args()


def run():
    logging.basicConfig(filename='/tmp/cgtd.log', level=logging.DEBUG)
    logging.debug('welcome')
    setlocale(LC_ALL, '')
    curses.wrapper(main, get_local_config(), parse_args())
