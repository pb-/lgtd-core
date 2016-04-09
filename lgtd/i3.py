import hmac
import sys
from json import loads

from websocket import create_connection

from .lib.util import get_local_config


def authenticate(ws, config):
    data = loads(ws.recv())
    mac = hmac.new(
        str(config['local_auth']), str(data['nonce'])).digest().encode('hex')
    ws.send('{"msg": "auth_response", "mac": "%s"}' % mac)
    data = loads(ws.recv())
    if data['msg'] != 'authenticated':
        raise Exception('authentication failed')


def run():
    config = get_local_config()
    ws = create_connection('ws://127.0.0.1:9001/gtd')
    authenticate(ws, config)
    ws.send('{"msg": "request_state", "tag": "inbox"}')
    data = loads(ws.recv())
    ws.close()

    tags = dict(map(lambda t: (t['name'], t['count']), data['state']['tags']))
    for i, tag in enumerate(sys.argv[1:]):
        if i > 0:
            sys.stdout.write(' ')
        count = str(tags[tag]) if tag in tags else '?'
        sys.stdout.write('{}:{}'.format(tag, count))
    sys.stdout.write('\n')
