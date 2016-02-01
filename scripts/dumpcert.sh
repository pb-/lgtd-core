#!/bin/sh

openssl x509 -in $1 -outform der -out /dev/stdout | python -c "from struct import unpack; from sys import stdin, stdout; data = stdin.read(); stdout.write('{'); map(lambda c: stdout.write('{}, '.format(unpack('b', c)[0])), data); stdout.write('}\\n');"
