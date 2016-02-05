import os
from argparse import ArgumentParser
from collections import defaultdict
from getpass import getpass
from sys import exit, stderr, stdin, stdout

from cryptography.exceptions import InvalidTag

from ..lib.crypto import CommandCipher, hash_password
from ..lib.db import ClientDatabase


def parse_args():
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    dump_parser = subparsers.add_parser('dump')
    dump_parser.add_argument('data_dir')
    dump_parser.add_argument(
        '-f', '--force', help='keep going when encountering unauthenticated '
        'commands (but still ignore them)', action='store_true')
    dump_parser.set_defaults(func=dump)

    encrypt_parser = subparsers.add_parser('encrypt')
    encrypt_parser.add_argument('app_id')
    encrypt_parser.set_defaults(func=encrypt)

    return parser.parse_args()


def get_keys():
    keys = []
    stderr.write(
        'You can supply multiple passwords and end with the empty password\n')

    num = 1
    while True:
        password = getpass('Password #{} (or enter): '.format(num))
        if not password:
            if num == 1:
                stdout.write('need at least one password\n')
                continue
            else:
                break

        keys.append(hash_password(password))
        num += 1

    return keys


def dump(args):
    keys = get_keys()
    db = ClientDatabase(args.data_dir)

    for line, app_id, offset in db.read_all(defaultdict(int)):
        decrypted = False
        for key in keys:
            cipher = CommandCipher(key)
            try:
                plaintext = cipher.decrypt(line, app_id, offset)
                stdout.write(plaintext)
                stdout.write('\n')
                decrypted = True
            except InvalidTag:
                pass

        if not decrypted and not args.force:
            stdout.write('\n')
            stderr.write('unable to decrypt command with any password!\n')
            stderr.write('use --force to ignore this problem\n')
            stderr.write(
                'the offending command is in app_id {} at offset {}\n'.format(
                    app_id, offset))
            stderr.write('its ciphertext reads:\n')
            stderr.write(line)
            exit(1)


def encrypt(args):
    out_offset = 0
    password = os.getenv('LGTD_PASSWORD')
    if password is None:
        raise Exception('Please provide the LGTD_PASSWORD environment var')
    key = hash_password(password)

    for line in stdin:
        stripped = line.strip()
        cipher = CommandCipher(key)
        ciphertext = cipher.encrypt(
            stripped, args.app_id, out_offset)
        stdout.write(ciphertext)
        out_offset += len(ciphertext)


def run():
    args = parse_args()
    args.func(args)
