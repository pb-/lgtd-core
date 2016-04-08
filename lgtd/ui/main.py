import curses
import hmac
import logging
import os
import re
import sys
from argparse import ArgumentParser
from datetime import date, timedelta
from json import dumps, loads
from locale import LC_ALL, setlocale
from select import error as select_error
from select import select
from threading import Thread

from websocket import WebSocketApp

from . import intent
from ..lib import commands
from ..lib.constants import ITEM_ID_LEN
from ..lib.util import get_local_config, random_string


ESC = 27
ENTER = 10

keymap = {
    'l': intent.PreviousTag,
    'K': intent.PreviousTag,
    'h': intent.NextTag,
    'J': intent.NextTag,
    'k': intent.PreviousItem,
    'j': intent.NextItem,
    'a': intent.AddItem,
    ENTER: intent.AddItem,
    'p': intent.Process,
    'd': intent.DeleteItem,
    'x': intent.DeleteItem,
    'i': intent.MoveToInbox,
    'D': intent.DeleteTag,
}

#keymap.update(
#    {chr(c): intent.SelectTag for c in range(ord('0'), ord('9') + 1)}
#)


class ParseError(Exception):
    pass


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


def parse_nat_date(s):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun'
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    t = re.compile('(in (\\d+)([dwmy])|on (mon|tue|wed|thu|fri|sat|sun|({}) '
                   '(\\d+)))'.format('|'.join(months)))
    m = t.match(s)
    if not m:
        raise ParseError("I do not understand that date format")

    tt = date.today()

    if m.group(1) and m.group(2):
        # in ...
        amt = int(m.group(2))
        u = m.group(3)
        if u == 'w':
            amt *= 7
        elif u == 'm':
            amt *= 30
        elif u == 'y':
            amt *= 365

        tt += timedelta(days=amt)
    elif m.group(5) and m.group(6):
        tt = tt.replace(month=months.index(m.group(5))+1, day=int(m.group(6)))
        if tt <= date.today():
            y = tt.year + 1
            tt = tt.replace(year=y)
    else:
        tt += timedelta(days=1)
        # this will livelock with the wrong locale.
        while tt.strftime('%a').lower() != m.group(4):
            tt += timedelta(days=1)

    return tt


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


def update_scroll(ui_state, key_offset, key_active):
    if not (ui_state[key_offset] <=
            ui_state[key_active] <
            ui_state[key_offset] + ui_state['content_height']):
        page, _ = divmod(ui_state[key_active], ui_state['content_height'])
        ui_state[key_offset] = page * ui_state['content_height']


def process_item_raw(state_adapter, item, query):
    # first, try to interpret it as a date
    try:
        date = '${}'.format(parse_nat_date(query))
        cmd = commands.SetTagCommand(item['id'], date)
        state_adapter.push_commands([cmd])
    except ParseError:
        pass

    if query.find(' ') != -1:
        return

    # otherwise, interpret as tag
    cmd = commands.SetTagCommand(item['id'], query)
    state_adapter.push_commands([cmd])


class Context(object):
    def __init__(self, model, adapter):
        self.set_state(Ready())
        self.model = model
        self.adapter = adapter
        self.vars = {
            'active_tag': 0,
            'active_item': 0,
            'scroll_offset_tags': 0,
            'scroll_offset_items': 0,
        }

    def set_state(self, state):
        self.state = state

    def handle_input(self, char):
        return self.state.handle_input(self, char)

    def handle_data(self, data):
        if data['msg'] == 'auth_challenge':
            self.adapter.authenticate(self.adapter.key, data['nonce'])
            self.adapter.request_state(
                self.model['tags'][self.vars['active_tag']]['name'])
        elif data['msg'] == 'new_state':
            self.adapter.request_state(
                self.model['tags'][self.vars['active_tag']]['name'])
        elif data['msg'] == 'state':
            self.model = {
                'tags': data['state']['tags'],
                'items': data['state']['items'],
            }
            self.vars['active_tag'] = data['state']['active_tag']


class State(object):
    def handle_input(self, context, char):
        raise NotImplemented


class Ready(State):
    def handle_input(self, context, char):
        if not 0 <= char <= 256:
            return False

        key = char if char in keymap else chr(char)
        if key not in keymap:
            return False

        keymap[key].execute(context, None)

        # scroll to make active item visible
        update_scroll(context.vars, 'scroll_offset_items', 'active_item')
        update_scroll(context.vars, 'scroll_offset_tags', 'active_tag')

        return True


class Input(State):
    def __init__(self):
        self.input_buffer = ''

    def handle_input(self, context, char):
        if 32 <= char < 256:
            self.input_buffer += chr(char)
        elif char == curses.KEY_BACKSPACE:
            if self.input_buffer:
                self.input_buffer = \
                    self.input_buffer.decode('utf-8')[:-1].encode('utf-8')
        elif char == ESC:
            context.set_state(Ready())
        elif char == ENTER:
            if self.input_buffer:
                self.submit(context)
            context.set_state(Ready())

        return True

    def submit(self, context):
        raise NotImplemented


class AddStuff(Input):
    def submit(self, context):
        set_title = commands.ItemTitleCommand(
            random_string(ITEM_ID_LEN), self.input_buffer)
        tag = context.model['tags'][context.vars['active_tag']]['name']
        if tag != 'inbox':
            set_tag = commands.SetTagCommand(set_title.item_id, tag)
            context.adapter.push_commands([set_title, set_tag])
        else:
            context.adapter.push_commands([set_title])


class Process(Input):
    def submit(self, context):
        item = context.model['items'][context.vars['active_item']]
        process_item_raw(context.adapter, item, self.input_buffer)


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
