from . import items
from ...lib import commands
from ...lib.constants import ITEM_ID_LEN
from ...lib.util import random_string
from .parser import ParseError, option, parse_args, positional, remainder


def dispatch(state, line):
    parts = line.split(' ')
    command = dispatch.commands.get(parts[0], unknown_command)
    try:
        args = parse_args(parts[1:], command.arguments)
    except AttributeError:
        args = []
    except ParseError as e:
        return state, None, str(e)

    return command(state, args)


def register(f):
    if not hasattr(dispatch, 'commands'):
        dispatch.commands = {}
    dispatch.commands[f.__name__] = f
    return f


@register
def all(state, _):
    return state, None, '\n'.join(
        items.render(item) for item in state['items'])


@register
@option('--start', '-s')
@option('--done', '-d')
@remainder('title')
def add(state, args):
    title = '#{} {}'.format(items.greatest(state['items']) + 1, args['title'])

    if args['start']:
        status = items.IN_PROGRESS
    elif args['done']:
        status = items.DONE
    else:
        status = items.TODO

    tag = items.TAG_PREFIX + status

    set_title = commands.ItemTitleCommand(random_string(ITEM_ID_LEN), title)
    set_tag = commands.SetTagCommand(set_title.item_id, tag)
    return state, map(str, (set_title, set_tag)), ''


def _set_status(state, status, num):
    item = items.find(state['items'], num or state['selected'])
    if not item:
        return state, None, 'no such item'
    else:
        set_tag = commands.SetTagCommand(item['id'], items.TAG_PREFIX + status)
        return state, [str(set_tag)], None


@register
@positional('num', type_=int, required=False)
def start(state, args):
    """Start working on a task (mark as in-progress)"""
    return _set_status(state, items.IN_PROGRESS, args['num'])


def unknown_command(state, _):
    return state, None, 'Unknown command'
