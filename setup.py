#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='lgtd-core',
    version='0.0.1',
    description='Core components of lgtd-suite',
    author='Paul Baecher',
    author_email='pbaecher@gmail.com',
    url='https://github.com/pb-/lgtd-core',
    packages=find_packages('.'),
    license='GPLv3',
    install_requires=[
        'tornado >=4.3',
    ],
    extras_require={
        'client': [
            'cryptography >=1.2.1,<2',
            'pyinotify >=0.9.6,<1',
            'requests >=2.9.1,<3',
            'websocket-client >=0.35.0,<1',
        ],
    },
    scripts=[
        'scripts/lgtd',
    ],
    entry_points={
        'console_scripts': [
            'lgtd_ui = lgtd.ui:run [client]',
            'lgtd_i3 = lgtd.i3:run [client]',
            'lgtd_d = lgtd.d:run [client]',
            'lgtd_sync = lgtd.sync.client:run [client]',
            'lgtd_syncd = lgtd.sync.server:run',
            'lgtd_dbadm = lgtd.tools.dbadm:run [client]',
        ],
    },
)
