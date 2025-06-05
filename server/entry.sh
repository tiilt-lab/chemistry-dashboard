#!/usr/bin/env bash

#perform initial db migrations
export FLASK_APP=discussion_capture.py
flask db upgrade

#create_user
python3 create_user_from.py blinc@mudcat11 super

exec "$@"
