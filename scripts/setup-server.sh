#!/bin/bash
set -e

pushd `dirname $0` > /dev/null
SCRIPTS=`pwd`
popd > /dev/null

echo "This script will create a dedicated TLS certificate for your"
echo "server. Since the client does hostname verification, you must"
echo "supply a correct fully-qualified hostname here."
echo ""
echo -n "hostname: "
read HOST

mkdir -p /var/lib/lgtd/data
cd /var/lib/lgtd

echo ""
"$SCRIPTS"/makecert.sh $HOST
echo ""

cd `dirname "$SCRIPTS"`

make build upd

echo "creating a repository for your data"
"$SCRIPTS"/makerepo.sh $HOST
echo ""

echo "Finally, copy the certificate /var/lib/lgtd/server.crt to the"
echo "client (to ~/.lgtd/server.crt)"
