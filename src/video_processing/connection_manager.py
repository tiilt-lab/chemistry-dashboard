# Shared implementation lives in src/common/connection_manager_impl.py
# (audio and video copies differed only by get_number_of_connections,
# which the shared version keeps). Shim preserves the bare-name import.
import os
import sys

_COMMON = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from connection_manager_impl import ConnectionManager  # noqa: F401,E402
