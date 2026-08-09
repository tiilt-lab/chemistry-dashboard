"""server/redis_helper delegates the shared RedisSessions reads to common.

The server kept a full copy of make_config_redis_key / make_auth_redis_key /
get_session_config / get_device_key that common/redis_client already defines.
The server class now inherits them; only the server-only writers + RedisLogin
remain here. (These modules need redis + a live config, so this is a
source-level contract; the real import is exercised by the service restart.)
"""
import os

_HELPER = os.path.join(os.path.dirname(__file__), "..", "src", "server", "redis_helper.py")


def _src():
    with open(_HELPER) as f:
        return f.read()


def test_server_redis_sessions_inherits_common():
    s = _src()
    assert "from redis_client import RedisSessions as _CommonRedisSessions" in s
    assert "class RedisSessions(_CommonRedisSessions):" in s


def test_shared_read_methods_are_not_redefined_in_the_server_copy():
    s = _src()
    for shared in ("def make_config_redis_key", "def make_auth_redis_key",
                   "def get_session_config", "def get_device_key"):
        assert shared not in s, f"{shared} must be inherited from common, not re-copied"


def test_server_only_methods_stay():
    s = _src()
    for kept in ("def create_session", "def create_device_key",
                 "def delete_device_key", "class RedisLogin"):
        assert kept in s
