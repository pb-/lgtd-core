import unittest
from collections import OrderedDict
from datetime import date, datetime

from mock import patch

from ..d import StateManager, delta_to_midnight


class DaemonTestCase(unittest.TestCase):
    @patch('lgtd.d.date')
    def test_state_mgr_render(self, mock_date):
        setattr(mock_date, 'today', lambda: date(2015, 12, 3))

        sm = StateManager(None, None, None)
        sm.state = {
            'tag_order': ['inbox', 'tickler', 'one', 'empty'],
            'items': OrderedDict([
                ('000', {'title': 'first item', 'tag': ''}),
                ('001', {'title': 'second item', 'tag': '$2015-12-04'}),
                ('002', {'title': '3rd item', 'tag': '$2015-12-03'}),
                ('003', {'title': 'item #4', 'tag': '$2015-12-02'}),
                ('004', {'title': 'other item', 'tag': 'one'}),
            ]),
        }

        expected = {
            'tags': [
                {'name': 'inbox', 'count': 3},
                {'name': 'tickler', 'count': 1},
                {'name': 'one', 'count': 1},
                {'name': 'empty', 'count': 0},
            ],
            'active_tag': 0,
            'items': [
                {'id': '000', 'title': 'first item'},
                {'id': '002', 'title': '3rd item', 'scheduled': '2015-12-03'},
                {'id': '003', 'title': 'item #4', 'scheduled': '2015-12-02'},
            ]
        }

        self.assertEqual(sm.render_state('inbox'), expected)

    @patch('lgtd.d.datetime')
    def test_midnight(self, mock_datetime):
        def now():
            return datetime(2016, 1, 31, 16, 48, 1, 49929)
        setattr(mock_datetime, 'now', now)
        expected = datetime(2016, 2, 1, 0, 5) - now()
        self.assertEqual(delta_to_midnight(), expected)

        def now():
            return datetime(2016, 1, 31)
        setattr(mock_datetime, 'now', now)
        expected = datetime(2016, 2, 1, 0, 5) - now()
        self.assertEqual(delta_to_midnight(), expected)

        def now():
            return datetime(2016, 1, 31, 0, 2, 56)
        setattr(mock_datetime, 'now', now)
        expected = datetime(2016, 2, 1, 0, 5) - now()
        self.assertEqual(delta_to_midnight(), expected)
