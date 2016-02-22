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
