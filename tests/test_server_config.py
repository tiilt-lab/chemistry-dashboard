"""src/server/config.py: the MySQL location keys.

The database URI used to hard-code localhost:3306. database_host/database_port
are optional config.ini keys so a development checkout can point at the MySQL
container from deploy/dev/docker-compose.yml on another port; existing
config.ini files without the keys must keep resolving to localhost:3306.
"""
import configparser
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "server"))

import config as cf  # noqa: E402


def _configure(values):
    parser = configparser.RawConfigParser(allow_no_value=True)
    parser.read_dict({"server": values})
    cf.config = parser


def test_database_location_defaults_to_localhost_3306():
    _configure({"database_user": "blinc"})
    assert cf.database_host() == "localhost"
    assert cf.database_port() == 3306


def test_database_location_reads_the_optional_keys():
    _configure({"database_user": "blinc", "database_host": "127.0.0.1", "database_port": "3307"})
    assert cf.database_host() == "127.0.0.1"
    assert cf.database_port() == 3307


def test_database_user_still_doubles_as_password():
    _configure({"database_user": "blinc"})
    assert cf.database_user() == "blinc:blinc"
