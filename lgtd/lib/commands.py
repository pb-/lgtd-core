from collections import OrderedDict
from itertools import chain

from .util import patch_order


class CommandRegistry(object):
    commands = {}

    @classmethod
    def register(cls, command_class):
        cls.commands[command_class.mnemonic] = command_class
        return command_class


class Command(object):
    mnemonic = None
    args = None

    def __init__(self, *args, **kwargs):
        attrs_set = set()
        for k, v in chain(zip(self.args, args), kwargs.iteritems()):
            setattr(self, k, v)
            attrs_set.add(k)

        if len(attrs_set) != len(self.args):
            raise ValueError('Too few arguments for command')

    def __str__(self):
        return ' '.join([self.mnemonic] + map(
            lambda arg: getattr(self, arg), self.args
        ))

    def __eq__(self, other):
        if self.mnemonic != other.mnemonic:
            return False

        for arg in self.args:
            if getattr(self, arg) != getattr(other, arg):
                return False

        return True

    @classmethod
    def parse_args(cls, string):
        parts = string.split(' ', len(cls.args) - 1)

        if len(parts) < len(cls.args):
            raise ValueError(
                'Not enough arguments to parse args: "{}"'.format(string)
            )

        return cls(*parts)

    @staticmethod
    def parse(string):
        mnemonic, args = string.split(' ', 1)
        command_class = CommandRegistry.commands[mnemonic]
        return command_class.parse_args(args)

    def apply(self, state):
        raise NotImplemented


@CommandRegistry.register
class OrderItemsCommand(Command):
    mnemonic = 'O'

    def __init__(self, *diffs):
        self.diffs = diffs

    def __str__(self):
        return self.mnemonic + ' ' + ' '.join(
            ','.join(num or '^' for num in diff)
            for diff in self.diffs
        )

    def __eq__(self, other):
        return self.mnemonic == other.mnemonic and self.diffs == other.diffs

    @classmethod
    def parse_args(cls, string):
        parts = string.split(' ')
        if len(parts) < 1:
            raise ValueError('Cannot parse: {}'.format(string))

        diffs = [
            [None if num == '^' else num for num in word.split(',')]
            for word in parts
        ]

        return cls(*diffs)

    def apply(self, state):
        old_items = state['items']
        nums = patch_order(old_items.keys(), self.diffs)

        state['items'] = OrderedDict()
        for num in nums:
            state['items'][num] = old_items[num]


@CommandRegistry.register
class ItemTitleCommand(Command):
    mnemonic = 't'
    args = ['item_id', 'title']

    def apply(self, state):
        if self.item_id not in state['items']:
            state['items'][self.item_id] = {'tag': ''}

        state['items'][self.item_id]['title'] = self.title


@CommandRegistry.register
class DeleteItemCommand(Command):
    mnemonic = 'd'
    args = ['item_id']

    def apply(self, state):
        try:
            del state['items'][self.item_id]
        except KeyError:
            pass


@CommandRegistry.register
class SetTagCommand(Command):
    mnemonic = 'T'
    args = ['item_id', 'tag']

    def apply(self, state):
        if self.tag in ('inbox', 'tickler'):
            return

        try:
            state['items'][self.item_id]['tag'] = self.tag
        except KeyError:
            pass
        else:
            if (self.tag not in state['tag_order'] and
                    not self.tag.startswith('$')):
                state['tag_order'].append(self.tag)


@CommandRegistry.register
class UnsetTagCommand(Command):
    mnemonic = 'D'
    args = ['item_id']

    def apply(self, state):
        try:
            state['items'][self.item_id]['tag'] = ''
        except KeyError:
            pass


@CommandRegistry.register
class OrderTagCommand(Command):
    mnemonic = 'o'
    args = ['first', 'second']

    def apply(self, state):
        order = state['tag_order']
        if self.first not in order or self.second not in order:
            return

        order.remove(self.second)
        order.insert(order.index(self.first) + 1, self.second)


@CommandRegistry.register
class DeleteTagCommand(Command):
    mnemonic = 'r'
    args = ['tag']

    def apply(self, state):
        if self.tag not in state['tag_order']:
            return
        if self.tag in ('inbox', 'tickler'):
            return

        for item in state['items'].values():
            if item['tag'] == self.tag:
                return  # don't remove non-empty tags

        state['tag_order'].remove(self.tag)
