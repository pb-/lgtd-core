from collections import OrderedDict
from curses import KEY_BACKSPACE

from . import intent
from ...lib import commands
from ...lib.constants import ITEM_ID_LEN, KEY_ENTER, KEY_ESC
from ...lib.util import ParseError, parse_natural_date, random_string


class Context(object):
    def __init__(self, model, adapter):
        self.set_state(Ready())
        self.model = model
        self.adapter = adapter
        self.vars = {
            'active_tag': 0,
            'active_item': 0,
            'scroll_offset_tags': 0,
            'scroll_offset_items': 0,
        }

    def set_state(self, state):
        self.state = state

    def handle_input(self, char):
        return self.state.handle_input(self, char)

    def handle_data(self, data):
        if data['msg'] == 'auth_challenge':
            self.adapter.authenticate(self.adapter.key, data['nonce'])
            self.adapter.request_state(
                self.model['tags'][self.vars['active_tag']]['name'])
        elif data['msg'] == 'new_state':
            self.adapter.request_state(
                self.model['tags'][self.vars['active_tag']]['name'])
        elif data['msg'] == 'state':
            self.model = {
                'tags': data['state']['tags'],
                'items': data['state']['items'],
            }
            self.vars['active_tag'] = data['state']['active_tag']


class State(object):
    def handle_input(self, context, char):
        raise NotImplemented


class Ready(State):
    def handle_input(self, context, char):
        if not 0 <= char <= 256:
            return False

        key = char if char in keymap else chr(char)
        if key not in keymap:
            return False

        intent, arg = keymap[key]
        intent.execute(context, arg)

        # scroll to make active item visible
        self.update_scroll(context, 'scroll_offset_items', 'active_item')
        self.update_scroll(context, 'scroll_offset_tags', 'active_tag')

        return True

    @staticmethod
    def update_scroll(context, key_offset, key_active):
        if not (context.vars[key_offset] <=
                context.vars[key_active] <
                context.vars[key_offset] + context.vars['content_height']):
            page, _ = divmod(
                context.vars[key_active], context.vars['content_height'])
            context.vars[key_offset] = page * context.vars['content_height']


class Help(State):
    def handle_input(self, context, _):
        context.set_state(Ready())
        return True


class Input(State):
    def __init__(self):
        self.input_buffer = ''

    def handle_input(self, context, char):
        if 32 <= char < 256:
            self.input_buffer += chr(char)
        elif char == KEY_BACKSPACE:
            if self.input_buffer:
                self.input_buffer = \
                    self.input_buffer.decode('utf-8')[:-1].encode('utf-8')
        elif char == KEY_ESC:
            context.set_state(Ready())
        elif char == KEY_ENTER:
            if self.input_buffer:
                self.submit(context)
            context.set_state(Ready())

        return True

    def submit(self, context):
        raise NotImplemented


class AddStuff(Input):
    def submit(self, context):
        set_title = commands.ItemTitleCommand(
            random_string(ITEM_ID_LEN), self.input_buffer)
        tag = context.model['tags'][context.vars['active_tag']]['name']
        if tag != 'inbox':
            set_tag = commands.SetTagCommand(set_title.item_id, tag)
            context.adapter.push_commands([set_title, set_tag])
        else:
            context.adapter.push_commands([set_title])


class Process(Input):
    def submit(self, context):
        item = context.model['items'][context.vars['active_item']]
        self.process_item_raw(context.adapter, item, self.input_buffer)

    @staticmethod
    def process_item_raw(adapter, item, query):
        # first, try to interpret it as a date
        try:
            date = '${}'.format(parse_natural_date(query))
            cmd = commands.SetTagCommand(item['id'], date)
            adapter.push_commands([cmd])
        except ParseError:
            pass

        if query.find(' ') != -1:
            return

        # otherwise, interpret as tag
        cmd = commands.SetTagCommand(item['id'], query)
        adapter.push_commands([cmd])


keymap = OrderedDict((
    ('l', (intent.PreviousTag, None)),
    ('K', (intent.PreviousTag, None)),
    ('h', (intent.NextTag, None)),
    ('J', (intent.NextTag, None)),
    ('g', (intent.FirstItem, None)),
    ('k', (intent.PreviousItem, None)),
    ('j', (intent.NextItem, None)),
    ('G', (intent.LastItem, None)),
    ('a', (intent.AddItem, AddStuff)),
    (KEY_ENTER, (intent.AddItem, AddStuff)),
    ('p', (intent.Process, Process)),
    ('d', (intent.DeleteItem, None)),
    ('x', (intent.DeleteItem, None)),
    ('i', (intent.MoveToInbox, None)),
    ('D', (intent.DeleteTag, None)),
    ('?', (intent.Help, Help)),
))

keymap.update(
    (chr(ord('0') + num), (intent.SelectTag, num)) for num in xrange(0, 10))
