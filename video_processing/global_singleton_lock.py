import threading

_DET = None
_LOCK = threading.Lock()

def get_detector(create_fn):
    """
    Lazily create and return the process-wide detector.
    The first caller must pass a zero-arg create_fn that builds/loads the model.
    Subsequent callers can pass None.
    """
    global _DET
    if _DET is None:
        with _LOCK:                 # protect first-time init
            if _DET is None:        # double-check inside lock
                _DET = create_fn()
    return _DET

def detector_lock():
    """A process-wide lock to serialize CUDA/YOLO calls."""
    return _LOCK