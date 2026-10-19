"""src/server/posthoc_state.py: the pure helpers (Redis is reached lazily).

Loaded from its file: other queue tests register a SimpleNamespace stub
under the name ``posthoc_state`` in sys.modules, which would shadow the
real module in the same pytest process."""
import importlib.util
import os

_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "server", "posthoc_state.py")
_spec = importlib.util.spec_from_file_location("posthoc_state_real", _PATH)
posthoc_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(posthoc_state)


def test_device_id_from_key_reads_the_pod_id_that_prefixes_a_processing_key():
    # The id lets a completion or failure callback clear the running flag of
    # a pod whose row was deleted mid-run (nothing else names it any more).
    assert posthoc_state.device_id_from_key("1451-3bd2617c-3444-45c2-87c5-d30a80b1785e") == 1451
    assert posthoc_state.device_id_from_key("7-x") == 7
    assert posthoc_state.device_id_from_key("abc-123") is None
    assert posthoc_state.device_id_from_key("") is None
    assert posthoc_state.device_id_from_key(None) is None
    assert posthoc_state.device_id_from_key("No key") is None
