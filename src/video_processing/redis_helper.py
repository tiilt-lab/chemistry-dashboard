# Shared implementation lives in src/common/redis_client.py (this file and
# the video_processing copy were byte-identical). The shim inserts common/
# on sys.path so the bare-name service imports keep working unchanged.
import os
import sys

_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from redis_client import RedisSessions  # noqa: F401,E402
