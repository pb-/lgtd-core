import hmac
import sys
from functools import partial
from json import dumps, loads
from operator import add
from select import select

from websocket import create_connection

from . import commands, items
from ...lib.util import get_local_config


def authenticate(read_fn, write_fn, secret):
    data = loads(read_fn())
    mac = hmac.new(
        str(secret), str(data['nonce'])).digest().encode('hex')
    write_fn('{"msg": "auth_response", "mac": "%s"}' % mac)
    data = loads(read_fn())
    if data['msg'] != 'authenticated':
        raise Exception('authentication failed')


def get_items(read_fn, write_fn, status):
    tag = items.TAG_PREFIX + status
    write_fn('{"msg": "request_state", "tag": "%s"}' % tag)
    state = loads(read_fn())['state']

    if state['tags'][state['active_tag']]['name'] == tag:
        return [
            dict(i.items() + [('status', status)] +
                 items.decode_title(i['title']).items())
            for i in state['items']
        ]
    else:
        return []


def get_state(read_fn, write_fn):
    status = (items.TODO, items.IN_PROGRESS, items.DONE, items.BLOCKED,
              items.DELETED)
    return reduce(add, map(partial(get_items, read_fn, write_fn), status))


def push_commands(commands):
    return dict(msg='push_commands', cmds=commands)


ws = create_connection('ws://127.0.0.1:9001/gtd')
authenticate(ws.recv, ws.send, get_local_config()['local_auth'])

state = dict(items=[], selected=None)

try:
    print('Welcome to tasks')
    print('Type "help" for help, use CTRL-D to exit')
    print('')
    while True:
        state['items'] = get_state(ws.recv, ws.send)
        if not state['selected']:
            state['selected'] = items.select_next(state['items'])
            if state['selected']:
                print('Now on ' + items.render(items.find(
                    state['items'], state['selected'])))
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
                state, network, stdout = commands.dispatch(
                    state, user_in.strip())
                if network:
                    ws.send(dumps(push_commands(network)))
                    ws.recv()
                if stdout:
                    print(stdout)
        if ws.sock in read_fds:
            ws.recv()  # unsolicited new state
finally:
    ws.close()
