import logging
import logging.handlers
import os
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timedelta
from json import dumps

import pyinotify
import requests

from ..lib.db.syncable import Database
from ..lib.util import (daemonize, ensure_lock_file, get_certificate_file,
                        get_data_dir, get_lock_file, get_sync_config)

SYNC_PERIODIC_INTERVAL = timedelta(minutes=15)
SYNC_DELAY = timedelta(seconds=10)
SYNC_RETRY_DELAY = timedelta(seconds=30)
REQUEST_TIMEOUT = timedelta(seconds=5)

logger = logging.getLogger(__name__)


def sync_url(config, op):
    return 'https://{}:{}/gtd/{}/{}'.format(
        config['host'], config['port'], config['sync_auth'], op)


class ProcessEvent(pyinotify.ProcessEvent):
    def my_init(self, db):
        self.schedule(timedelta())
        self.db = db

    def schedule(self, delta):
        logger.debug('scheduling next sync in %s' % delta)
        self.next_sync = datetime.now() + delta

    def timeout(self):
        return max(
            0, int((self.next_sync - datetime.now()).total_seconds() * 1000))

    def process_default(self, event):
        logger.debug('change notification')

        with self.db.lock(True):
            local_offs = self.db.get_offsets()

        # if there are no changes, sync immediately
        # else use delay
        if local_offs == self.last_local_offs:
            self.schedule(timedelta())
        else:
            self.schedule(SYNC_DELAY)


def make_request(url, data):
    response = requests.post(
        url, data=data, timeout=REQUEST_TIMEOUT.total_seconds(),
        verify=get_certificate_file())
    response.raise_for_status()
    return response


def sync(config, db):
    with db.lock(True):
        local_offs = db.get_offsets()

    logger.debug('sync: pull')
    response = make_request(
        sync_url(config, 'pull'), dumps({'offs': local_offs}))
    response.raise_for_status()
    remote = response.json()
    if remote['data'] and db.is_gapless(local_offs, remote['data']):
        if db.is_gapless(local_offs, remote['data']):
            logger.debug('sync: new data from pull')
            with db.lock():
                db.insert_data(local_offs, remote['data'])

    with db.lock(True):
        missing_data = db.get_missing_data(
            local_offs, defaultdict(int, remote['offs']))
        if missing_data:
            logger.debug('sync: push')
            make_request(
                sync_url(config, 'push'), dumps({'data': missing_data}))
        else:
            logger.debug('sync: no push needed')


def try_sync(config, db):
    try:
        start = datetime.now()
        logger.info('syncing now...')
        sync(config, db)
    except requests.exceptions.RequestException:
        logger.exception('sync failed: ')
        return False
    finally:
        logger.info('sync done, took {}'.format(datetime.now() - start))

    return True


def loop(config, db):
    wm = pyinotify.WatchManager()
    wm.add_watch(get_lock_file(), pyinotify.IN_CLOSE_WRITE)
    pe = ProcessEvent(db=db)
    notifier = pyinotify.Notifier(wm, pe)

    while True:
        with db.lock(True):
            pe.last_local_offs = db.get_offsets()

        logger.debug('waiting for events up to %d ms' % pe.timeout())
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


def parse_args():
    parser = ArgumentParser(description='synchronization service for lgtd')
    parser.add_argument(
        '-d', '--daemon', action='store_true', help='fork into background')
    return parser.parse_args()


def run():
    ensure_lock_file()
    cert = get_certificate_file()
    if not os.path.isfile(cert):
        raise ValueError('no certificate at found at {}'.format(cert))

    config = get_sync_config()
    if not config['host'] or not config['sync_auth']:
        raise ValueError('sync host or auth not configured')

    args = parse_args()

    if args.daemon:
        logger.setLevel(logging.INFO)
        handler = logging.handlers.SysLogHandler('/dev/log')
        handler.setFormatter(logging.Formatter('%(name)s %(message)s'))
        logger.addHandler(handler)

        pid = os.fork()
        if pid:
            return 0
        daemonize()
    else:
        logging.basicConfig(level=logging.DEBUG)

    loop(config, Database(get_data_dir(), get_lock_file()))
