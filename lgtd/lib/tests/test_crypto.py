import unittest
from struct import pack, unpack

from cryptography.exceptions import InvalidTag

from ..crypto import CommandCipher


class CipherTestCase(unittest.TestCase):
    def test_generate_iv(self):
        for _ in xrange(100):
            iv = unpack('>Q', CommandCipher.generate_iv())[0]
            self.assertEqual(iv & 0xf, 0)

    def test_extract_time(self):
        ciphertext = 'VqdrlN+V/3 mkhjHvOytEUdD+eZwoVCFg kYAXsUr1x2m2'
        time = CommandCipher.extract_time(ciphertext)
        self.assertEqual(time, 1453812628.894)

    def test_iv_coding(self):
        encoded = CommandCipher.encode_iv(pack('>Q', 0xb8e95aa4fd6bde80))
        self.assertEqual(encoded, 'uOlapP1r3o')
        decoded = unpack('>Q', CommandCipher.decode_iv(encoded))[0]
        self.assertEqual(decoded, 0xb8e95aa4fd6bde80)

    def test_padding(self):
        self.assertEqual(CommandCipher.padded(''), '')
        self.assertEqual(CommandCipher.padded('aa'), 'aa==')
        self.assertEqual(CommandCipher.padded('aaa'), 'aaa=')

        self.assertEqual(CommandCipher.unpadded(''), '')
        self.assertEqual(CommandCipher.unpadded('AA=='), 'AA')
        self.assertEqual(CommandCipher.unpadded('AAA='), 'AAA')
        self.assertEqual(CommandCipher.unpadded('AAAA'), 'AAAA')

    def test_cipher(self):
        real_cipher = CommandCipher('x' * 32)
        bad_cipher = CommandCipher('x' * 31 + 'y')
        secret = 'secret message'
        client_id = 'ab'
        offset = 489174

        # good case
        ciphertext = real_cipher.encrypt(secret, client_id, offset)
        self.assertTrue(ciphertext.endswith('\n'))
        plaintext = real_cipher.decrypt(ciphertext, client_id, offset)
        self.assertEqual(plaintext, secret)

        # test authenticated data
        with self.assertRaises(InvalidTag):
            real_cipher.decrypt(ciphertext, 'ba', offset)
        with self.assertRaises(InvalidTag):
            real_cipher.decrypt(ciphertext, client_id, offset + 1)

        # test different key
        with self.assertRaises(InvalidTag):
            bad_cipher.decrypt(ciphertext, client_id, offset)

        # test malformed data (iv, tag, and ciphertext)
        bad_ciphertext = ciphertext[:4] + 'x' + ciphertext[5:]
        with self.assertRaises(InvalidTag):
            real_cipher.decrypt(bad_ciphertext, client_id, offset)
        bad_ciphertext = ciphertext[:14] + 'x' + ciphertext[15:]
        with self.assertRaises(InvalidTag):
            real_cipher.decrypt(bad_ciphertext, client_id, offset)
        bad_ciphertext = ciphertext[:44] + 'x' + ciphertext[45:]
        with self.assertRaises(InvalidTag):
            real_cipher.decrypt(bad_ciphertext, client_id, offset)
