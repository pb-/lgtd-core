import unittest
from itertools import permutations

from mock import patch

from ..util import compare_digest, diff_order, patch_order


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

    def test_diff_order(self):
        with self.assertRaises(ValueError):
            diff_order([1, 2, None, 3], [])

        with self.assertRaises(ValueError):
            diff_order([1], [1, 2])

        with self.assertRaises(ValueError):
            diff_order([1, 2], [1, 3])

        a = 'abcdef'
        self.assertEqual(diff_order(a, a), [])

        b = 'fabcde'
        self.assertEqual(diff_order(a, b), [[None, 'f']])

        b = 'fbcdea'
        self.assertEqual(diff_order(a, b), [[None, 'f'], ['e', 'a']])

        b = 'defabc'
        self.assertEqual(diff_order(a, b), [[None, 'd', 'e', 'f']])

        b = 'abdcef'
        self.assertEqual(diff_order(a, b), [['b', 'd']])

    def test_patch_order(self):
        with self.assertRaises(ValueError):
            patch_order([1, None, 2], [])

        with self.assertRaises(ValueError):
            patch_order([], [[1, 2, 2]])

        items = list('abcdef')
        self.assertEqual(patch_order(items, [[]]), items)

        diff = [[None, 'f']]
        self.assertEqual(patch_order(items, diff), list('fabcde'))

        diff = [['b', 'd']]
        self.assertEqual(patch_order(items, diff), list('abdcef'))

        diff = [['x', 'd']]
        self.assertEqual(patch_order(items, diff), items)

        diff = [['x', 'y']]
        self.assertEqual(patch_order(items, diff), items)

        diff = [['a', 'x', 'y']]
        self.assertEqual(patch_order(items, diff), items)

        diff = [['a', None]]
        self.assertEqual(patch_order(items, diff), items)

    def test_diff_patch_order(self):
        a = list('abcdef')
        for b in permutations(a):
            self.assertEqual(patch_order(a, diff_order(a, b)), list(b))
