#!/bin/sh

dd if=/dev/urandom count=1 bs=30 2>/dev/null | base64 | sed -e 's/[\/+]//g' | cut -c -10
