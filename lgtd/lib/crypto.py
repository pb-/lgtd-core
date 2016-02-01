import os
from base64 import b64decode, b64encode
from calendar import timegm
from datetime import datetime
from hashlib import sha256
from struct import pack, unpack

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def hash_password(password):
    salt = '\xf8\x99\x8a\x8c\x2a\x3a\x94\x08\x61\x83\x0a\x4d\xab\x62\xfe\x46'
    password = password.encode('utf-8') if isinstance(password, unicode) \
        else password

    h = sha256()
    h.update(salt)
    h.update(password)

    return h.digest()


class CommandCipher(object):
    def __init__(self, key):
        self.key = key

    @staticmethod
    def generate_iv():
        t = datetime.utcnow()
        # 32 bits time seconds
        sec = timegm(t.timetuple())
        # 10 bits msec
        msec = t.microsecond // 1000
        # 18 bits random
        r = unpack('I', os.urandom(4))[0] & 0x3ffff

        iv = (sec << 28) | (msec << 18) | r
        # align iv to use the 60 high bits of a 64 bit int
        iv <<= 4
        return pack('>Q', iv)

    @staticmethod
    def encode_iv(iv):
        return b64encode(iv)[:10]

    @staticmethod
    def decode_iv(encoded_iv):
        return b64decode(encoded_iv + 'A=')

    @staticmethod
    def extract_time(ciphertext):
        iv = unpack('>Q', CommandCipher.decode_iv(ciphertext[:10]))[0] >> 4
        # strip random
        iv >>= 18
        msec = iv & 0x3ff
        iv >>= 10

        return iv + float(msec) / 1000

    @staticmethod
    def unpadded(padded):
        if padded:
            if padded[-2] == '=':
                return padded[:-2]
            elif padded[-1] == '=':
                return padded[:-1]
            else:
                return padded
        else:
            return padded

    @staticmethod
    def padded(unpadded):
        remainder = len(unpadded) % 4
        if remainder:
            return unpadded + '=' * (4 - remainder)
        else:
            return unpadded

    @staticmethod
    def format_auth_data(client_id, offset):
        return '{} {}'.format(client_id, offset)

    def encrypt(self, plaintext, client_id, offset):
        iv = self.generate_iv()
        encryptor = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()

        encryptor.authenticate_additional_data(
            self.format_auth_data(client_id, offset))
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return '{} {} {}\n'.format(
            self.encode_iv(iv),
            self.unpadded(b64encode(encryptor.tag)),
            self.unpadded(b64encode(ciphertext)),
        )

    def decrypt(self, ciphertext, client_id, offset):
        iv, tag, ciphertext = ciphertext.strip().split(' ')
        iv = self.decode_iv(iv)
        tag = b64decode(self.padded(tag))
        ciphertext = b64decode(self.padded(ciphertext))

        decryptor = Cipher(
            algorithms.AES(self.key),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()

        decryptor.authenticate_additional_data(
            self.format_auth_data(client_id, offset))

        return decryptor.update(ciphertext) + decryptor.finalize()
