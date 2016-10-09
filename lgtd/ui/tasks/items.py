import re
from itertools import chain

TAG_PREFIX = '@w-'

BLOCKED = 'blocked'
DELETED = 'deleted'
DONE = 'done'
IN_PROGRESS = 'in-progress'
TODO = 'todo'


def iter_status(items, status):
    return (item for item in items if item['status'] == status)


def iter_backlog(tasks):
    return chain(
        iter_status(tasks, IN_PROGRESS),
        iter_status(tasks, TODO),
    )


def iter_all(tasks):
    return chain(
        iter_backlog(tasks),
        iter_status(tasks, BLOCKED),
        iter_status(tasks, DONE),
        iter_status(tasks, DELETED),
    )


def iter_standup(tasks):
    return chain(
        reversed(list(iter_status(tasks, DONE))),
        iter_backlog(tasks),
        iter_status(tasks, BLOCKED),
    )


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
        (('#{}'.format(item['n']), ) if item['n'] is not None else ()) +
        (('[{}]'.format(item['dt']), ) if item['dt'] is not None else ()) +
        (item['title'], )
    )


def select_next(items):
    try:
        return next(iter_backlog(items))['n']
    except StopIteration:
        return None


def find(items, n):
    try:
        return next(item for item in items if item['n'] == n)
    except StopIteration:
        return None


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


def render(item, colorizer=shell_color):
    color = {
        TODO: 'blue',
        IN_PROGRESS: 'yellow',
        DONE: 'green',
        DELETED: 'normal',
        BLOCKED: 'red',
    }.get(item['status'], 'gray')

    return ' '.join(
        (colorizer('gray', '#{}'.format(item['n'])),
            colorizer(color, item['status'])) +
        ('[{}]'.format(item['dt'], ) if item['dt'] is not None else ()) +
        (colorizer('white', item['title']), )
    )
