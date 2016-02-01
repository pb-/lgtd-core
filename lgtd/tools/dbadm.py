from argparse import ArgumentParser
from collections import defaultdict
from getpass import getpass
from sys import exit, stderr, stdout

from cryptography.exceptions import InvalidTag

from ..lib.crypto import CommandCipher, hash_password
from ..lib.db import ClientDatabase


def get_args():
    parser = ArgumentParser()
    parser.add_argument('command', choices=['dump'])
    parser.add_argument('data_dir')
    parser.add_argument('-f', '--force', help='keep going when encountering '
                        'unauthenticated commands (but still ignore them)',
                        action='store_true')
    parser.add_argument('-e', '--encrypt', metavar='APP_ID', help='re-encrypt '
                        'all commands under a new password and use APP_ID for '
                        'the new application id')
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


def get_new_key():
    return hash_password(getpass('New password for re-encryption: '))


def dump(args, keys, db, new_key):
    out_offset = 0

    for line, app_id, offset in db.read_all(defaultdict(int)):
        decrypted = False
        for key in keys:
            cipher = CommandCipher(key)
            try:
                plaintext = cipher.decrypt(line, app_id, offset)
                if args.encrypt:
                    cipher = CommandCipher(new_key)
                    ciphertext = cipher.encrypt(
                        plaintext, args.encrypt, out_offset)
                    stdout.write(ciphertext)
                    out_offset += len(ciphertext)
                else:
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


def run():
    args = get_args()
    keys = get_keys()
    db = ClientDatabase(args.data_dir)
    new_key = get_new_key() if args.encrypt else None

    if args.command == 'dump':
        dump(args, keys, db, new_key)
