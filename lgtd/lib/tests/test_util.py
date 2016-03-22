import unittest

from mock import patch

from ..util import compare_digest


class UtilTest(unittest.TestCase):
    @patch('lgtd.lib.util.hmac')
    def test(self, hmac):
        # make sure we hit the code path where the native compare_digest
        # is not available (python < 2.7.7)
        hmac.compare_digest.side_effect = AttributeError('mocked out')

        self.assertTrue(compare_digest('', ''))
        self.assertTrue(compare_digest('a\xff', 'a\xff'))
        self.assertFalse(compare_digest('a\xff', ''))
        self.assertFalse(compare_digest('a\xff', 'a\xfe'))
