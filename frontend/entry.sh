#!/usr/bin/env bash

nginx -c /etc/nginx/nginx.conf

nginx -t
nginx -s reload

exec "$@"
