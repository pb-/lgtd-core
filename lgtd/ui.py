import curses
import logging
import os
import random
import re
import sys
from datetime import date, timedelta
from json import dumps, loads
from select import error as select_error
from select import select
from threading import Thread

from websocket import WebSocketApp

ITEM_ID_LEN = 3
IM_ADD = 0
IM_EDIT = 1
IM_PROC = 2


class ParseError(Exception):
    pass


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


def clamp_index(array, index):
    if not array:
        return 0
    return max(0, min(len(array)-1, index))


def gen_id(id_len):
    alpha = ['{}'.format(x) for x in xrange(10)] + \
            [chr(x) for x in xrange(ord('A'), ord('Z')+1)] + \
            [chr(x) for x in xrange(ord('a'), ord('z')+1)]

    return ''.join((random.choice(alpha) for x in xrange(id_len)))


ui_state = {
    'active_tag': 0,
    'active_item': 0,
    'scroll_offset_tags': 0,
    'scroll_offset_items': 0,
    'input_mode': None,
}


class WindowTooSmallError(Exception):
    pass


def content_height(scr):
    # usable height minus: title bar, pad, pad, status bar (4)
    ymax, _ = scr.getmaxyx()
    return ymax - 4


def render(scr, model_state, ui_state):
    scr.erase()
    (y, x) = scr.getmaxyx()
    col = curses.color_pair(1)
    scr.addstr(0, 0, ' ' * x, col)
    scr.addstr(0, 2, 'GTD', col)
    #if ui_state['dirty']:
    #    scr.addstr(0, 5, '*', col)
    #if ui_state['syncing']:
    #    scr.addstr(0, x - 2, 'S', col)

    height = content_height(scr)
    if height < 1:
        raise WindowTooSmallError()

    for i, tag in enumerate(model_state['tags']):
        if i < ui_state['scroll_offset_tags']:
            continue
        ii = i - ui_state['scroll_offset_tags']
        if not ii < height:
            break

        scr.addnstr(ii+2, 3, tag['name'], 9)
        if tag['count']:
            scr.addstr(' ({})'.format(tag['count']))
        if i == ui_state['active_tag']:
            scr.addstr(ii+2, 1, '|')

    for i, item in enumerate(model_state['items']):
        if i < ui_state['scroll_offset_items']:
            continue
        ii = i - ui_state['scroll_offset_items']
        if not ii < height:
            break

        scr.addstr(ii+2, 20, item['title'])
        if 'scheduled' in item:
            scr.addstr('  [{}]'.format(
                item['scheduled']), curses.color_pair(2))
        if i == ui_state['active_item']:
            scr.addstr(ii+2, 18, '>')

    if ui_state['input_mode'] is not None:
        curses.curs_set(1)
        scr.addstr(y-1, 2, '> ' + ui_state['input_buffer'])
        scr.move(y-1, 4+ui_state['input_cursor_pos'])
    else:
        curses.curs_set(0)

    scr.refresh()


def update_scroll(ui_state, key_offset, key_active):
    if not (ui_state[key_offset] <=
            ui_state[key_active] <
            ui_state[key_offset] + ui_state['content_height']):
        page, _ = divmod(ui_state[key_active], ui_state['content_height'])
        ui_state[key_offset] = page * ui_state['content_height']


def validate_indexes(model_state, ui_state):
    ui_state['active_tag'] = clamp_index(
        model_state,
        ui_state['active_tag'])
    ui_state['active_item'] = clamp_index(
        model_state[ui_state['active_tag']],
        ui_state['active_item'])


def process_item_raw(model_state, item, query):
    # first, try to interpret it as a date
    try:
        date = '$' + parse_nat_date(query).isoformat()
        tc = SetTagCommand(item.id, date)
        model_state = eval_local_command(model_state, tc)
        model_state = model_state.update_scheduled()
        return model_state
    except ParseError:
        pass

    if query.find(' ') != -1:
        return model_state

    # next, try to find a tag that matches
    tag = query
    try:
        tag = model_state.find_tag(query).name
    except ValueError:
        pass

    try:
        ti, _ = model_state.find_item_index(item.id)
    except ValueError:
        return model_state

    if tag != model_state[ti].name:
        tc = SetTagCommand(item.id, tag)
        return eval_local_command(model_state, tc)


def handle_input(ch, state_mgr, model_state, ui_state):
    if ui_state['input_mode'] is not None:
        if 32 <= ch < 256:
            before = ui_state['input_buffer'][:ui_state['input_cursor_pos']]
            after = ui_state['input_buffer'][ui_state['input_cursor_pos']:]
            ui_state['input_buffer'] = before + chr(ch) + after
            ui_state['input_cursor_pos'] += 1
        elif ch == curses.KEY_BACKSPACE:
            if ui_state['input_cursor_pos'] > 0:
                before = \
                    ui_state['input_buffer'][:ui_state['input_cursor_pos']-1]
                after = ui_state['input_buffer'][ui_state['input_cursor_pos']:]
                ui_state['input_buffer'] = before + after
                ui_state['input_cursor_pos'] -= 1
        elif ch == 27 or ch == 10:
            im = ui_state['input_mode']
            ui_state['input_mode'] = None
            if ch == 27 or not ui_state['input_buffer']:
                return True

            if im == IM_ADD:
                tc = TitleCommand(gen_id(ITEM_ID_LEN),
                                  ui_state['input_buffer'])
                model_state = eval_local_command(model_state, tc)
                tag = model_state[ui_state['active_tag']].name
                if tag != 'inbox':
                    tc = SetTagCommand(tc.item_id, tag)
                    model_state = eval_local_command(model_state, tc)
            elif im == IM_PROC:
                item = model_state[ui_state['active_tag']][
                    ui_state['active_item']]
                model_state = process_item_raw(
                    model_state, item, ui_state['input_buffer'])

        return True
    else:
        if ch == ord('l') or ch == ord('K'):
            active = max(0, ui_state['active_tag']-1)
            if ui_state['active_tag'] != active:
                ui_state['active_item'] = 0
                ui_state['active_tag'] = active
                state_mgr.request_state(model_state['tags'][active]['name'])
        elif ch == ord('h') or ch == ord('J'):
            active = min(len(model_state)-1, ui_state['active_tag']+1)
            if ui_state['active_tag'] != active:
                ui_state['active_item'] = 0
                ui_state['active_tag'] = active
                state_mgr.request_state(model_state['tags'][active]['name'])
        elif ch == ord('k'):
            ui_state['active_item'] = max(0, ui_state['active_item']-1)
        elif ch == ord('j'):
            ui_state['active_item'] = min(
                len(model_state['items'])-1,
                ui_state['active_item']+1)
        elif ch == ord('a') or ch == 10:
            ui_state['input_mode'] = IM_ADD
            ui_state['input_cursor_pos'] = 0
            ui_state['input_buffer'] = ''
        elif (ch == ord('p') and ui_state['active_tag'] == 0 and
                len(model_state[0])):
            ui_state['input_mode'] = IM_PROC
            ui_state['input_cursor_pos'] = 0
            ui_state['input_buffer'] = ''
        elif ((ch == ord('d') or ch == ord('x')) and
                len(model_state[ui_state['active_tag']])):
            item_id = model_state[ui_state['active_tag']][
                ui_state['active_item']
            ].id
            dc = DeleteItemCommand(item_id)
            model_state = eval_local_command(model_state, dc)
        elif (ch == ord('i') and ui_state['active_tag'] and
                len(model_state[ui_state['active_tag']])):
            item_id = model_state[ui_state['active_tag']][
                ui_state['active_item']
            ].id
            uc = UnsetTagCommand(item_id)
            model_state = eval_local_command(model_state, uc)
        elif (ch == ord('D') and model_state[ui_state['active_tag']].name
                not in DEFAULT_TAGS and not
                len(model_state[ui_state['active_tag']])):
            dt = DeleteTagCommand(
                model_state[ui_state['active_tag']].name)
            model_state = eval_local_command(model_state, dt)
        elif ord('0') <= ch <= ord('9'):
            num = (ch - ord('0') + 9) % 10
            if num < len(model_state) and num != ui_state['active_tag']:
                ui_state['active_tag'] = num
                ui_state['active_item'] = 0
        else:
            return False

        # scroll to make active item visible
        update_scroll(ui_state, 'scroll_offset_items', 'active_item')
        update_scroll(ui_state, 'scroll_offset_tags', 'active_tag')

        return True


class StateManagerThread(Thread):
    msg_size_len = 10
    msg_size_fmt = '{:0%d}' % msg_size_len

    def __init__(self):
        super(StateManagerThread, self).__init__()
        self.read_fd, self.write_fd = os.pipe()

    def _send(self, msg):
        os.write(self.write_fd, self.msg_size_fmt.format(len(msg)))
        os.write(self.write_fd, msg)

    def stop(self):
        self.socket.close()

    def recv(self):
        msg_size = int(os.read(self.read_fd, self.msg_size_len))
        return loads(os.read(self.read_fd, msg_size))

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

    def _on_open(self, socket):
        self._send('{"msg": "new_state"}')

    def _on_message(self, socket, message):
        self._send(message)

    def run(self):
        self.socket = WebSocketApp(
            'ws://127.0.0.1:9001/gtd',
            on_open=self._on_open,
            on_message=self._on_message)

        self.socket.run_forever()


def main(scr):
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.noecho()
    curses.cbreak()
    scr.keypad(1)
    ui_state['content_height'] = content_height(scr)

    state_mgr = StateManagerThread()
    state_mgr.start()

    model_state = {
        'tags': [{'name': 'inbox', 'count': 0}],
        'items': [],
    }

    while True:
        render(scr, model_state, ui_state)

        try:
            selected, _, _ = select([sys.stdin, state_mgr.read_fd], [], [])
        except select_error:
            curses.resizeterm(*scr.getmaxyx())
            scr.refresh()
            selected = []
        if sys.stdin in selected:
            key = scr.getch()
            consumed = handle_input(key, state_mgr, model_state, ui_state)
            if not consumed:
                if key == ord('q'):
                    break
        if state_mgr.read_fd in selected:
            data = state_mgr.recv()
            logging.debug('GOT MSG {}'.format(data))
            if data['msg'] == 'new_state':
                state_mgr.request_state(
                    model_state['tags'][ui_state['active_tag']]['name'])
            elif data['msg'] == 'state':
                model_state = {
                    'tags': data['state']['tags'],
                    'items': data['state']['items'],
                }
                ui_state['active_tag'] = data['state']['active_tag']

    # tear down websocket connection and wait for thread to end
    state_mgr.stop()
    state_mgr.join()


def setup():
    global key, local_id, server
    logging.basicConfig(filename='/tmp/cgtd.log', level=logging.DEBUG)
    logging.debug('welcome')

    #gtd_dir = os.path.join(os.getenv('HOME'), '.gtd', 'data')
    #mkdir_p(gtd_dir)
    #local_id = read_local_id()
    #server = read_server()

    #model_state = ModelState(Tag(t) for t in DEFAULT_TAGS)

    curses.wrapper(main)

if __name__ == '__main__':
    setup()
