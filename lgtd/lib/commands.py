from itertools import chain


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

    @staticmethod
    def parse(string):
        mnemonic = string[0]
        command_class = CommandRegistry.commands[mnemonic]
        parts = string.split(' ', len(command_class.args))

        if len(parts) < 1 + len(command_class.args):
            raise ValueError(
                'Not enough arguments to parse command: "{}"'.format(string)
            )

        return command_class(*parts[1:])

    def apply(self, state):
        raise NotImplemented


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
        try:
            state['items'][self.item_id]['tag'] = self.tag
        except KeyError:
            pass


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
