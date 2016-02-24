import errno
import json
import os
import random
from stat import S_IRUSR, S_IWUSR

from .constants import APP_ID_LEN, LOCAL_AUTH_LEN


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
