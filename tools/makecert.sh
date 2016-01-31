#!/bin/bash
HOST="$1"

openssl req \
    -x509 \
    -subj "/C=US/ST=CA/O=WongDong Ltd./CN=$HOST" \
    -extensions SAN \
    -config <(cat \
        /etc/ssl/openssl.cnf \
	<(printf "[SAN]\nsubjectAltName=DNS:$HOST\n")) \
    -sha256 \
    -nodes \
    -days 1000 \
    -newkey rsa:2048 \
    -keyout server.key \
    -out server.crt
