import errno
import os


def get_lgtd_dir():
    return os.path.join(os.getenv('HOME'), '.lgtd')


def get_lock_file():
    return os.path.join(get_lgtd_dir(), 'lock')


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
