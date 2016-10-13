import os
import re

from . import items
from ...lib import commands
from ...lib.constants import ITEM_ID_LEN
from ...lib.util import diff_order, random_string
from .parser import ParseError, option, parse_args, positional, remainder


def dispatch(state, line):
    parts = line.split(' ')
    cmd = dispatch.aliases.get(parts[0])
    command = dispatch.commands.get(cmd or parts[0], unknown_command)
    try:
        args = parse_args(parts[1:], command.arguments)
    except AttributeError:
        args = []
    except ParseError as e:
        return state, None, str(e)

    return command(state, args)


def alias(*aliases):
    def wrapper(f):
        for a in aliases:
            dispatch.aliases[a] = f.__name__
        return f

    if not hasattr(dispatch, 'aliases'):
        dispatch.aliases = {}
    return wrapper


def register(f):
    if not hasattr(dispatch, 'commands'):
        dispatch.commands = {}
    dispatch.commands[f.__name__] = f
    return f


def list_items(state, items_):
    return state, None, items.render_list(items_)


@register
@alias('ls', 'list')
def all(state, _):
    return list_items(state, items.iter_all(state['items']))


@register
@alias('bl')
def backlog(state, _):
    return list_items(state, items.iter_backlog(state['items']))


@register
@alias('su')
def standup(state, _):
    return list_items(state, items.iter_standup(state['items']))


@register
@alias('s')
def status(state, _):
    item = items.find(state['items'], state['selected'])
    return state, None, 'Currently on ' + items.render(item)


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
    """Start working on a task (mark as in-progress)."""
    return _set_status(state, items.IN_PROGRESS, args['num'])


@register
@positional('num', type_=int, required=False)
def done(state, args):
    """Complete a task (mark as done)."""
    return _set_status(state, items.DONE, args['num'])


@register
@positional('num', type_=int, required=False)
def block(state, args):
    """Mark a task as blocked."""
    return _set_status(state, items.BLOCKED, args['num'])


@register
@positional('num', type_=int, required=False)
def delete(state, args):
    """Delete a task (mark as deleted)."""
    return _set_status(state, items.DELETED, args['num'])


@register
def clear(state, _):
    """Clear screen."""
    os.system('clear')
    return state, None, None


@register
@positional('num', type_=int, required=False)
def edit(state, args):
    """Change the title of an item."""
    item = items.find(state['items'], args['num'] or state['selected'])
    path = os.path.join('/tmp', 'tasks.{}.edit'.format(os.getpid()))

    open(path, 'w').write(item['title'])
    os.system('editor {}'.format(path))
    title = open(path).read().strip()
    os.remove(path)

    if title:
        encoded = items.encode_title(dict(item.items() + [('title', title)]))
        set_title = commands.ItemTitleCommand(item['id'], encoded)
        return state, [str(set_title)], None
    else:
        return state, None, 'Rejecting edit: title is empty'


@register
def order(state, _):
    """Re-order back log in an external editor."""
    path = os.path.join('/tmp', 'tasks.{}.edit'.format(os.getpid()))
    backlog = list(items.iter_backlog(state['items']))
    old_order = [item['n'] for item in backlog]
    open(path, 'w').write(items.render_list(backlog, lambda _, text: text))
    os.system('editor {}'.format(path))

    new_order = []
    pattern = re.compile(r'^ *#(?P<num>\d+) ')
    with open(path) as f:
        for line in f:
            match = pattern.match(line)
            if match:
                new_order.append(int(match.group('num')))

    os.remove(path)

    try:
        num_diffs = diff_order(old_order, new_order)
        if num_diffs:
            diffs = [
                [num and items.find(state['items'], num)['id'] for num in diff]
                for diff in num_diffs
            ]
            return state, [str(commands.OrderItemsCommand(*diffs))], None
        else:
            return state, None, None
    except ValueError:
        return state, None, 'Reorder failed: set of items has changed'


def unknown_command(state, _):
    return state, None, 'Unknown command'
