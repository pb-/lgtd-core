import errno
import hmac
import json
import os
import random
import re
from contextlib import contextmanager
from datetime import date, timedelta
from difflib import SequenceMatcher
from locale import LC_ALL, setlocale
from stat import S_IRUSR, S_IWUSR

from dateutil.relativedelta import relativedelta

from .constants import APP_ID_LEN, LOCAL_AUTH_LEN


class ParseError(Exception):
    pass


def get_lgtd_dir():
    return os.path.join(os.getenv('HOME'), '.lgtd')


def get_lock_file():
    return os.path.join(get_lgtd_dir(), 'lock')


def get_certificate_file():
    return os.path.join(get_lgtd_dir(), 'server.crt')


def get_data_dir():
    return os.path.join(get_lgtd_dir(), 'data')


def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def ensure_data_dir():
    ensure_dir(get_data_dir())


def ensure_lock_file():
    path = get_lock_file()
    if os.path.isfile(path):
        return

    ensure_dir(get_lgtd_dir())
    with open(path, 'a'):
        pass


def random_string(length):
    alpha = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    return ''.join((random.choice(alpha) for _ in xrange(length)))


def get_config(conf_file, default_content_handler, create_new=False):
    path = os.path.join(get_lgtd_dir(), conf_file)

    if create_new:
        ensure_dir(get_lgtd_dir())
        with open(path, 'w') as f:
            json.dump(default_content_handler(), f, indent=2, sort_keys=True)
            f.write('\n')
        os.chmod(path, S_IRUSR | S_IWUSR)

    try:
        with open(path) as f:
            return json.load(f)
    except IOError:
        if create_new:
            raise
        else:
            # retry with creating a new file
            return get_config(conf_file, default_content_handler, True)


def get_local_config():
    return get_config('local.conf.json', lambda: {
        'app_id': random_string(APP_ID_LEN),
        'local_auth': random_string(LOCAL_AUTH_LEN),
    })


def get_sync_config():
    return get_config('sync.conf.json', lambda: {
        'host': '',
        'port': 9002,
        'sync_auth': '',
    })


def compare_digest(a, b):
    try:
        return hmac.compare_digest(a, b)
    except AttributeError:
        # compare_digest() was only added in 2.7.7
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)

        return result == 0


def daemonize():
    os.setsid()
    os.chdir('/')

    null = open(os.devnull, 'w')
    os.dup2(null.fileno(), 1)  # stdout
    os.dup2(null.fileno(), 2)  # stderr


@contextmanager
def locale(l):
    old = setlocale(LC_ALL)
    try:
        yield setlocale(LC_ALL, l)
    finally:
        setlocale(LC_ALL, old)


def parse_natural_date(s):
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    t = re.compile(
        r'(?P<relative>in (?P<magnitude>\d+)(?P<unit>[dwmy])|'
        r'on ((?P<weekday>mon|tue|wed|thu|fri|sat|sun)|'
        r'(?P<month>{}) (?P<day>\d+)))'.format('|'.join(months)))
    m = t.match(s)
    if not m:
        raise ParseError("I do not understand that date format")

    tt = date.today()

    if m.group('relative') and m.group('magnitude'):
        # in ...
        amt = int(m.group('magnitude'))
        u = m.group('unit')
        if u == 'w':
            tt += timedelta(weeks=amt)
        elif u == 'm':
            tt += relativedelta(months=amt)
        elif u == 'y':
            tt += relativedelta(years=amt)
        else:
            tt += timedelta(days=amt)
    elif m.group('month') and m.group('day'):
        try:
            tt = tt.replace(
                month=months.index(m.group('month'))+1,
                day=int(m.group('day')))
        except ValueError as e:
            raise ParseError(e)
        if tt <= date.today():
            tt += relativedelta(years=1)
    else:
        tt += timedelta(days=1)
        with locale('C'):
            while tt.strftime('%a').lower() != m.group('weekday'):
                tt += timedelta(days=1)

    return tt


def diff_order(a, b):
    """
    For two permutations a and b, compute a diff (delta) that turns a into b.
    """
    if None in list(a):
        raise ValueError('sequence must not contain None')
    elif len(a) != len(b) or set(a) != set(b):
        raise ValueError('"a" is not a permutation of "b"')

    return [
        [None if start == 0 else b[start - 1]] + list(b[start:end])
        for tag, _, _, start, end in SequenceMatcher(None, a, b).get_opcodes()
        if tag in ('insert', 'replace')
    ]


def patch_order(items, diffs):
    """
    Apply a diff that was created with diff_order(). For any elements in the
    diff that are not present in items, fail gracefully and do not add them to
    items. In other words, maintain the invariant that whatever is returned
    is a permutation of items, no matter what the diff is.
    """
    if None in list(items):
        raise ValueError('items must not contain None')

    reordered = [None] + list(items)
    for diff in diffs:
        if len(diff) != len(set(diff)):
            raise ValueError('malformed diff')

        diff = [x for i, x in enumerate(diff)
                if x in reordered and (not i or x)]
        if diff:
            anchor, seq = diff[0], diff[1:]
            offset = reordered.index(anchor)

            reordered = [
                x for x in reordered[:offset + 1] if x not in seq
            ] + seq + [
                x for x in reordered[offset + 1:] if x not in seq
            ]

    return reordered[1:]
