#!/bin/sh
set -e

REPO=$(base64 -w 0 < /dev/urandom | tr -d +/ | dd bs=10 count=1 2> /dev/null)
DIR=/var/lib/lgtd/data/$REPO

echo "creating $DIR"
mkdir -p $DIR

cat <<EOF
repo created; set up ~/.lgtd/sync.conf.json on the client
as follows (don't forget to change the host!):

{
  "host": "example.com",
  "port": 9002,
  "sync_auth": "${REPO}"
}
EOF
