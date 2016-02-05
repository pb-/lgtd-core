import sys
from json import loads

from websocket import create_connection


def run():
    ws = create_connection('ws://127.0.0.1:9001/gtd')
    ws.send('{"msg": "request_state", "tag": "inbox"}')
    data = loads(ws.recv())
    ws.close()

    tags = dict(map(lambda t: (t['name'], t['count']), data['state']['tags']))
    for i, tag in enumerate(sys.argv[1:]):
        if i > 0:
            sys.stdout.write(' ')
        count = str(tags[tag]) if tag in tags else '?'
        sys.stdout.write('{}:{}'.format(tag, count))
