import unittest
from collections import defaultdict
from json import dumps

from ..server import parse_pull_input, parse_push_input


class ServerTestCase(unittest.TestCase):
    def test_parse_pull_good(self):
        good = {
            'offs': {
                '00': 190582,
                'ab': 1,
                'Q8': 193491,
            },
        }
        self.assertEqual(parse_pull_input(dumps(good)), good)

        good = {
            'offs': {
            },
        }
        self.assertEqual(parse_pull_input(dumps(good)), good)

    def test_parse_pull_bad(self):
        bads = [{  # empty
            }, {
                'offs': 10,  # wrong type of value
            }, {
                'offs': {
                    'foo': 1,  # invalid app_id
                },
            }, {
                'offs': {
                    'foo': '100',  # wrong type of value
                },
            }, {
                'offs': {
                    'ab': -38,  # value not in range
                },
            },
        ]

        for bad in bads:
            with self.assertRaises(ValueError):
                parse_pull_input(dumps(bad))

    def test_parse_push_good(self):
        good = {
            'data': {
                'ab': [102, 'abc abc ...'],
                'Q8': [1024818, 'foo'],
            },
        }
        self.assertEqual(parse_push_input(dumps(good)), good)

    def test_parse_push_bad(self):
        bads = [{  # empty
            }, {
                'data': 102,  # wrong value type
            }, {
                'data': {
                    'foo': [1, 'abc'],  # wrong app_id
                },
            }, {
                'data': {
                    'Qa': 42,  # wrong value type
                },
            }, {
                'data': {
                    'Qa': [1],  # wrong list len
                },
            }, {
                'data': {
                    'Qa': ['1', '2'],  # wrong type (first item)
                },
            }, {
                'data': {
                    'Qa': [1, 2],  # wrong type (second item)
                },
            }, {
                'data': {
                    'Qa': [1, ''],  # invalid empty string
                }
            },
        ]

        for bad in bads:
            with self.assertRaises(ValueError):
                parse_push_input(dumps(bad))
