"""Shared config helpers for the audio & video services.

Both config.py modules repeated `str(x) in ['true','True','t','1']` ~15 times
and carried byte-identical redis_host/redis_port/redis_db accessors. Those live
once in common/config_base now.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "common"))

from config_base import as_bool, redis_host, redis_port, redis_db  # noqa: E402


def test_as_bool_truthy_strings():
    for v in ("true", "True", "t", "1", 1, True):
        assert as_bool(v) is True, v


def test_as_bool_falsey_strings():
    for v in ("false", "False", "0", "", "no", "off", None, 0, False):
        assert as_bool(v) is False, v


class _FakeConfig:
    def __init__(self, values):
        self.values = values

    def get(self, section, option, fallback=None):
        return self.values.get((section, option), fallback)


def test_redis_accessors_read_the_redis_section():
    cfg = _FakeConfig({
        ("redis", "redis_host"): "cache.internal",
        ("redis", "redis_port"): "6380",
        ("redis", "redis_db"): "2",
    })
    assert redis_host(cfg) == "cache.internal"
    assert redis_port(cfg) == 6380
    assert redis_db(cfg) == 2


def test_redis_accessors_fall_back_to_defaults():
    cfg = _FakeConfig({})
    assert redis_host(cfg) == "localhost"
    assert redis_port(cfg) == 6379
    assert redis_db(cfg) == 0
