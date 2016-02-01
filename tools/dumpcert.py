#!/usr/bin/python
from struct import unpack
from sys import stdin, stdout

data = stdin.read()
stdout.write('{')
for c in data:
    stdout.write('{}, '.format(unpack('b', c)[0]))
stdout.write('}\n')
