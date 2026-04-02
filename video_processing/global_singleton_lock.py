import threading

_OBJECT_DETECTION = None
_ATTENTION_PREDICTION = None
_EMOTION_PREDICTION = None
_OBJECT_DETECTION_LOCK = threading.Lock()
_ATTENTION_EMOTION_PREDICTION_LOCK = threading.Lock()

def get_object_detector(create_fn):
    """
    Lazily create and return the process-wide detector.
    The first caller must pass a zero-arg create_fn that builds/loads the model.
    Subsequent callers can pass None.
    """
    global _OBJECT_DETECTION
    if _OBJECT_DETECTION is None:
        with _OBJECT_DETECTION_LOCK:                 # protect first-time init
            if _OBJECT_DETECTION is None:        # double-check inside lock
                _OBJECT_DETECTION = create_fn()
    return _OBJECT_DETECTION

def get_attention_emotion_predictor(create_attention_fn, create_emotion_fn):
    """
    Lazily create and return the process-wide attention/emotion predictor.
    The first caller must pass a zero-arg create_fn that builds/loads the model.
    Subsequent callers can pass None.
    """
    global _ATTENTION_PREDICTION, _EMOTION_PREDICTION
    if _ATTENTION_PREDICTION is None and _EMOTION_PREDICTION is None:
        with _ATTENTION_EMOTION_PREDICTION_LOCK:                 # protect first-time init
            if _ATTENTION_PREDICTION is None and _EMOTION_PREDICTION is None:        # double-check inside lock
                _ATTENTION_PREDICTION = create_attention_fn()
                _EMOTION_PREDICTION = create_emotion_fn()
    return _ATTENTION_PREDICTION, _EMOTION_PREDICTION

def object_detector_lock():
    """A process-wide lock to serialize CUDA/YOLO calls."""
    return _OBJECT_DETECTION_LOCK

def attention_emotion_predictor_lock():
    """A process-wide lock to serialize CUDA/attention/emotion prediction calls."""
    return _ATTENTION_EMOTION_PREDICTION_LOCK