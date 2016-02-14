import unittest
from collections import OrderedDict

from ..commands import (Command, DeleteItemCommand, DeleteTagCommand,
                        ItemTitleCommand, OrderTagCommand, SetTagCommand,
                        UnsetTagCommand)


class CommandsTestCase(unittest.TestCase):
    def test_encode_decode(self):
        cmd = ItemTitleCommand('000', 'the quick brown fox')
        self.assertEqual(str(cmd), 't 000 the quick brown fox')

        parsed_cmd = Command.parse(str(cmd))
        self.assertEqual(cmd, parsed_cmd)

    def test_equality(self):
        a = DeleteItemCommand('000')
        self.assertEqual(a, a)

        b = DeleteItemCommand('000')
        self.assertEqual(a, b)

        c = UnsetTagCommand('000')
        self.assertNotEqual(a, c)

        d = DeleteItemCommand('001')
        self.assertNotEqual(a, d)

    def test_bad_init(self):
        with self.assertRaises(ValueError):
            ItemTitleCommand('000')  # title missing

    def test_bad_encoding(self):
        encoded = 't 000'  # title missing
        with self.assertRaises(ValueError):
            Command.parse(encoded)

    @staticmethod
    def get_state():
        return {
            'tag_order': ['t1', 't2', 't3'],
            'items': OrderedDict([
                ('i00', {'title': 'the first item', 'tag': 't1'}),
                ('i01', {'title': 'the second item', 'tag': 't1'}),
            ]),
        }

    def test_item_title_command(self):
        state = self.get_state()
        ItemTitleCommand('i99', 'some item').apply(state)
        self.assertIn('i99', state['items'])
        self.assertEqual(state['items']['i99']['title'], 'some item')
        self.assertEqual(state['items']['i99']['tag'], '')

        ItemTitleCommand('i00', 'new title').apply(state)
        self.assertEqual(state['items']['i00']['title'], 'new title')

    def test_delete_item_command(self):
        state = self.get_state()
        DeleteItemCommand('i44').apply(state)  # i44 does not exist
        self.assertEqual(state, self.get_state())

        DeleteItemCommand('i00').apply(state)
        self.assertNotIn('i00', state['items'])

    def test_set_tag_command(self):
        state = self.get_state()
        SetTagCommand('i44', 't9').apply(state)  # i44 does not exist
        self.assertEqual(state, self.get_state())

        SetTagCommand('i00', 't2').apply(state)
        self.assertEqual(state['items']['i00']['tag'], 't2')
        self.assertEqual(state['tag_order'], ['t1', 't2', 't3'])

        SetTagCommand('i00', '$2016-01-01').apply(state)
        self.assertEqual(state['items']['i00']['tag'], '$2016-01-01')
        self.assertEqual(state['tag_order'], ['t1', 't2', 't3'])

        SetTagCommand('i01', 'new').apply(state)
        self.assertEqual(state['tag_order'][-1], 'new')
        self.assertEqual(state['items']['i01']['tag'], 'new')

    def test_unset_tag_command(self):
        state = self.get_state()
        UnsetTagCommand('i44').apply(state)  # i44 does not exist
        self.assertEqual(state, self.get_state())

        UnsetTagCommand('i00').apply(state)
        self.assertEqual(state['items']['i00']['tag'], '')

    def test_order_tag_command(self):
        state = self.get_state()
        OrderTagCommand('t9', 't1').apply(state)  # t9 does not exist
        OrderTagCommand('t1', 't9').apply(state)  # t9 does not exist
        OrderTagCommand('t1', 't2').apply(state)  # already in this order
        self.assertEqual(state, self.get_state())

        OrderTagCommand('t2', 't1').apply(state)
        self.assertEqual(state['tag_order'], ['t2', 't1', 't3'])

    def test_delete_tag_command(self):
        state = self.get_state()
        DeleteTagCommand('t9').apply(state)  # does not exist
        DeleteTagCommand('t1').apply(state)  # tag not empty
        self.assertEqual(state, self.get_state())

        DeleteTagCommand('t2').apply(state)
        self.assertNotIn('t2', state['tag_order'])

    @staticmethod
    def get_special_state():
        return {
            'tag_order': ['inbox', 'tickler', 'other'],
            'items': OrderedDict([
                ('i00', {'title': 'the first item', 'tag': 'other'}),
                ('i01', {'title': 'the second item', 'tag': 'other'}),
            ]),
        }

    def test_special_tags(self):
        state = self.get_special_state()

        SetTagCommand('i00', 'inbox').apply(state)  # not directly setable
        SetTagCommand('i01', 'tickler').apply(state)  # not directly setable
        self.assertEqual(state, self.get_special_state())

        DeleteTagCommand('inbox').apply(state)  # not deletable
        DeleteTagCommand('tickler').apply(state)  # not deletable
        self.assertEqual(state, self.get_special_state())
