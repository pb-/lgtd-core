#!/usr/bin/env python
from setuptools import setup

setup(
    name='lgtd server',
    version='0.0.0',
    description='Server components for lgtd',
    author='Paul Baecher',
    author_email='pbaecher@gmail.com',
    url='https://github.com/pb-/gtd-server',
    packages=['lgtd'],
    entry_points={
        'console_scripts': [
            'lgtd_server = lgtd.server:run',
        ],
    },
)
