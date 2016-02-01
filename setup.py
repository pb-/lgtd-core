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
    entry_points={
        'console_scripts': [
            'lgtd = lgtd.ui:run',
            'lgtd_d = lgtd.d:run',
            'lgtd_sync = lgtd.sync.client:run',
            'lgtd_syncd = lgtd.sync.server:run',
            'lgtd_dbadm = lgtd.tools.dbadm:run',
        ],
    },
)
