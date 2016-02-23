#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='lgtd-suite',
    version='0.0.0',
    description='Python components for lgtd',
    author='Paul Baecher',
    author_email='pbaecher@gmail.com',
    url='https://github.com/pb-/lgtd-suite',
    packages=find_packages('.'),
    install_requires=[
        'cryptography >=1.2.1,<2',
        'pyinotify >=0.9.6,<1',
        'requests >=2.9.1,<3',
        'tornado >=4.3',
        'websocket-client >=0.35.0,<1',
    ],
    scripts=[
        'scripts/lgtd',
    ],
    entry_points={
        'console_scripts': [
            'lgtd_ui = lgtd.ui:run',
            'lgtd_i3 = lgtd.i3:run',
            'lgtd_d = lgtd.d:run',
            'lgtd_sync = lgtd.sync.client:run',
            'lgtd_syncd = lgtd.sync.server:run',
            'lgtd_dbadm = lgtd.tools.dbadm:run',
        ],
    },
)
