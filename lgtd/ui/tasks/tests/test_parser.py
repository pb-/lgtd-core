from unittest import TestCase

from ..parser import ParseError, option, parse_args, positional, remainder


class ParserTest(TestCase):
    def testparse_args(self):
        @option('--debug', '-d')
        @option('--verbose', '-v')
        @positional('a')
        @positional('b')
        @positional('c', required=False, default='x')
        @remainder('rest')
        def some_func():
            pass

        line = '   z  -v -d 20 10 foo  bar'
        parsed = parse_args(line.split(' '), some_func.arguments)
        self.assertEqual(parsed, {
            'debug': True,
            'verbose': True,
            'a': 'z',
            'b': '20',
            'c': '10',
            'rest': 'foo  bar',
        })

        line = ' --debug z 20 --  foo bar --verbose'
        parsed = parse_args(line.split(' '), some_func.arguments)
        self.assertEqual(parsed, {
            'debug': True,
            'verbose': False,
            'a': 'z',
            'b': '20',
            'c': 'x',
            'rest': ' foo bar --verbose',
        })

        with self.assertRaises(ParseError):
            line = '--debug z -- foo bar --verbose'
            parse_args(line.split(' '), some_func.arguments)
