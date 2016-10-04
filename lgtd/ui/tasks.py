import hmac
import re
import sys
from functools import partial
from itertools import chain
from json import dumps, loads
from operator import add
from select import select

from websocket import create_connection

from ..lib import commands
from ..lib.constants import ITEM_ID_LEN
from ..lib.util import get_local_config, random_string

TAG_PREFIX = '@w-'
TODO = 'todo'
IN_PROGRESS = 'in-progress'
DONE = 'done'
DELETED = 'deleted'
BLOCKED = 'blocked'


def authenticate(read_fn, write_fn, secret):
    data = loads(read_fn())
    mac = hmac.new(
        str(secret), str(data['nonce'])).digest().encode('hex')
    write_fn('{"msg": "auth_response", "mac": "%s"}' % mac)
    data = loads(read_fn())
    if data['msg'] != 'authenticated':
        raise Exception('authentication failed')


def greatest(items):
    return max(chain((0, ), (
            item['n'] for item in items if item['n'] is not None
        )
    ))


def decode_title(title):
    match = re.match(
        r'^(#(?P<n>\d+) )?(\[(?P<dt>[^\]]*)\] )?(?P<title>.+)$', title)
    n = match.group('n')

    return dict(
        n=n and int(n),
        dt=match.group('dt'),
        title=match.group('title'),
    )


def encode_title(item):
    return ' '.join(
        ('#{} '.format(item['n']), ) if item['n'] is not None else () +
        ('[{}] '.format(item['dt']), ) if item['dt'] is not None else () +
        (item['title'], )
    )


def get_items(read_fn, write_fn, status):
    tag = TAG_PREFIX + status
    write_fn('{"msg": "request_state", "tag": "%s"}' % tag)
    state = loads(read_fn())['state']

    if state['tags'][state['active_tag']]['name'] == tag:
        return [
            dict(i.items() + [('status', status)] +
                 decode_title(i['title']).items())
            for i in state['items']
        ]
    else:
        return []


def get_state(read_fn, write_fn):
    status = (TODO, IN_PROGRESS)
    return reduce(add, map(partial(get_items, read_fn, write_fn), status))


def select_next(items):
    try:
        return next(item for item in items
                    if item['status'] in (TODO, IN_PROGRESS))['n']
    except StopIteration:
        return None


def find(items, n):
    try:
        return next(item for item in items if item['n'] == n)
    except StopIteration:
        return None


def push_commands(commands):
    return dict(msg='push_commands', cmds=commands)


def add_item(state, title, status=TODO):
    if not title:
        return state, None, 'no title given'

    title = '#{} {}'.format(greatest(state['items']) + 1, title)

    set_title = commands.ItemTitleCommand(random_string(ITEM_ID_LEN), title)
    set_tag = commands.SetTagCommand(set_title.item_id, TAG_PREFIX + status)
    return state, map(str, (set_title, set_tag)), ''


def set_status(state, status, num=None):
    item = find(state['items'], num or state['selected'])
    if not item:
        return state, None, 'nothing to start'
    else:
        set_tag = commands.SetTagCommand(item['id'], TAG_PREFIX + status)
        return state, [str(set_tag)], None


def start(state, num=None):
    return set_status(state, IN_PROGRESS, num and int(num))


def shell_color(color, text):
    code = {
        'blue': '1;34',
        'gray': '1;30',
        'green': '1;32',
        'normal': '0',
        'red': '1;31',
        'white': '0;37',
        'yellow': '1;33',
    }.get(color)

    return '\033[{code}m{text}\033[0m'.format(code=code, text=text)


def render_item(item, colorizer=shell_color):
    color = {
        TODO: 'blue',
        IN_PROGRESS: 'yellow',
        DONE: 'green',
        DELETED: 'normal',
        BLOCKED: 'red',
    }.get(item['status'], 'gray')

    return '{} {} {}'.format(
        colorizer('gray', '#{}'.format(item['n'])),
        colorizer(color, item['status']),
        colorizer('white', item['title'])
    )


def all_items(state, _):
    return state, None, '\n'.join(
        render_item(item) for item in state['items'])


def unknown_command(state, _):
    return state, None, 'unknown command'


def dispatch(state, line):
    commands = {
        'all': all_items,
        'add': add_item,
        'start': start,
    }

    parts = line.split(' ', 1)
    args = parts[1] if len(parts) > 1 else None
    return commands.get(parts[0], unknown_command)(state, args)


ws = create_connection('ws://127.0.0.1:9001/gtd')
authenticate(ws.recv, ws.send, get_local_config()['local_auth'])


state = dict(items=[], selected=None)

try:
    while True:
        state['items'] = get_state(ws.recv, ws.send)
        if not state['selected']:
            state['selected'] = select_next(state['items'])
        if state['selected']:
            sys.stdout.write('#{}'.format(state['selected']))
        sys.stdout.write('> ')
        sys.stdout.flush()
        read_fds, _, _ = select([sys.stdin, ws.sock], [], [])

        if sys.stdin in read_fds:
            user_in = sys.stdin.readline()
            if not user_in:
                sys.stdout.write('\n')
                break
            elif user_in.strip():
                state, network, stdout = dispatch(state, user_in.strip())
                if network:
                    ws.send(dumps(push_commands(network)))
                    ws.recv()
                if stdout:
                    print(stdout)
        if ws.sock in read_fds:
            ws.recv()  # unsolicited new state
finally:
    ws.close()
