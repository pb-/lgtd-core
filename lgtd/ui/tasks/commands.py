from . import actions, items


def all_items(state, _):
    return state, None, '\n'.join(
        items.render(item) for item in state['items'])


def unknown_command(state, _):
    return state, None, 'unknown command'


def dispatch(state, line):
    commands = {
        'all': all_items,
        'add': actions.add,
        'start': actions.start,
    }

    parts = line.split(' ', 1)
    args = parts[1] if len(parts) > 1 else None
    return commands.get(parts[0], unknown_command)(state, args)
