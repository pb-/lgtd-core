import logging
from collections import defaultdict
from datetime import datetime, timedelta
from json import dumps

import pyinotify
import requests

from ..lib.db import SyncableDatabase
from ..lib.util import (ensure_lock_file, get_data_dir, get_lock_file,
                        get_sync_config)

SYNC_PERIODIC_INTERVAL = timedelta(minutes=15)
SYNC_DELAY = timedelta(seconds=10)
SYNC_RETRY_DELAY = timedelta(seconds=30)
REQUEST_TIMEOUT = timedelta(seconds=5)
logging.basicConfig(level=logging.DEBUG)


def sync_url(config, op):
    # TODO change to https (only)
    return 'http://{}:{}/gtd/{}/{}'.format(
        config['host'], config['port'], config['sync_auth'], op)


class ProcessEvent(pyinotify.ProcessEvent):
    def my_init(self):
        self.schedule(timedelta())

    def schedule(self, delta):
        logging.debug('scheduling next sync in %s' % delta)
        self.next_sync = datetime.now() + delta

    def timeout(self):
        return max(
            0, int((self.next_sync - datetime.now()).total_seconds() * 1000))

    def process_default(self, event):
        logging.debug('change notification')

        # if there are no changes, sync immediately
        # else use delay
        self.schedule(SYNC_DELAY)


def make_request(url, data):
    # TODO verify=
    response = requests.post(
        url, data=data, timeout=REQUEST_TIMEOUT.total_seconds())
    response.raise_for_status()
    return response


def sync(config, db):
    with db.lock(True):
        local_offs = db.get_offsets()

    logging.debug('sync: pull')
    response = make_request(
        sync_url(config, 'pull'), dumps({'offs': local_offs}))
    remote = response.json()
    if remote['data'] and db.is_gapless(local_offs, remote['data']):
        if db.is_gapless(local_offs, remote['data']):
            logging.debug('sync: new data from pull')
            with db.lock():
                db.insert_data(local_offs, remote['data'])

    with db.lock(True):
        missing_data = db.get_missing_data(
            local_offs, defaultdict(int, remote['offs']))
        if missing_data:
            logging.debug('sync: push')
            make_request(
                sync_url(config, 'push'), dumps({'data': missing_data}))
        else:
            logging.debug('sync: no push needed')


def try_sync(config, db):
    try:
        logging.debug('syncing now...')
        sync(config, db)
    except requests.exceptions.RequestException as e:
        logging.exception(e)
        return False
    finally:
        logging.debug('sync done.')

    return True


def loop(config, db):
    wm = pyinotify.WatchManager()
    wm.add_watch(get_lock_file(), pyinotify.IN_CLOSE_WRITE)
    pe = ProcessEvent()
    notifier = pyinotify.Notifier(wm, pe)

    while True:
        logging.debug('waiting for events up to %d ms' % pe.timeout())
        if notifier.check_events(pe.timeout()):
            notifier.read_events()
            notifier.process_events()

        if datetime.now() >= pe.next_sync:
            if try_sync(config, db):
                pe.schedule(SYNC_PERIODIC_INTERVAL)
            else:
                pe.schedule(SYNC_RETRY_DELAY)

            # consume and ignore any events that piled up during sync
            # (might have been us but we cannot tell for sure)
            if notifier.check_events(0):
                notifier.read_events()
                wm.set_ignore_events(True)
                notifier.process_events()
                wm.set_ignore_events(False)


def run():
    ensure_lock_file()
    loop(get_sync_config(), SyncableDatabase(get_data_dir(), get_lock_file()))
