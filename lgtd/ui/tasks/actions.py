from . import items
from ...lib import commands
from ...lib.constants import ITEM_ID_LEN
from ...lib.util import random_string


def add(state, title, status=items.TODO):
    if not title:
        return state, None, 'no title given'

    title = '#{} {}'.format(items.greatest(state['items']) + 1, title)
    tag = items.TAG_PREFIX + status

    set_title = commands.ItemTitleCommand(random_string(ITEM_ID_LEN), title)
    set_tag = commands.SetTagCommand(set_title.item_id, tag)
    return state, map(str, (set_title, set_tag)), ''


def set_status(state, status, num=None):
    item = items.find(state['items'], num or state['selected'])
    if not item:
        return state, None, 'nothing to start'
    else:
        set_tag = commands.SetTagCommand(item['id'], items.TAG_PREFIX + status)
        return state, [str(set_tag)], None


def start(state, num=None):
    return set_status(state, items.IN_PROGRESS, num and int(num))
