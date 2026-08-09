"""Shared config helpers for the audio & video processing services.

Both config.py modules repeated the same INI-boolean idiom
(``str(x) in ['true','True','t','1']``) ~15 times each and carried
byte-identical redis_host/redis_port/redis_db accessors. They live here once.
The redis accessors take the service's configparser ``config`` so this module
stays free of per-service module globals.
"""

_TRUE = ('true', 'True', 't', '1')


def as_bool(value):
    """The services' INI truthiness rule: a value is on iff its string form is
    one of true/True/t/1. (RawConfigParser returns strings; this also accepts
    real bools/ints.)"""
    return str(value) in _TRUE


def redis_host(config):
    return str(config.get('redis', 'redis_host', fallback='localhost'))


def redis_port(config):
    return int(config.get('redis', 'redis_port', fallback=6379))


def redis_db(config):
    return int(config.get('redis', 'redis_db', fallback=0))
