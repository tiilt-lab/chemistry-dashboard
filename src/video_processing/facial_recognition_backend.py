"""Face detection + embedding backend, selected via [videoprocessing]
``face_model`` in config.ini (through config.py ``face_model()``):

  * 'dlib'        -- the original ``face_recognition`` (dlib) 128-D ResNet
                     encoder. Default; behaviour is byte-for-byte unchanged.
  * 'insightface' -- ArcFace ``buffalo_l`` (512-D). Open SOTA, far more robust
                     to pose/lighting. Lazily imported so its absence never
                     breaks the default path.

IMPORTANT — the two backends are NOT interchangeable on existing data:
  * Embeddings differ in dimensionality (128 vs 512) and scale, so an enrolled
    gallery (.npy) is backend-specific. Switching face_model requires
    re-enrolling every student.
  * Match thresholds differ. dlib uses ``distance < 0.5`` on face_distance;
    ArcFace uses cosine similarity (higher = closer). ``match_params()`` returns
    the backend-appropriate cutoffs so the matcher can stay backend-agnostic.

Both the enrollment service (facial_biometric_processing_service.py) and the
inference matcher (attention_tracking/detect.py) go through this single module
so they can never drift apart.
"""

import logging
import numpy as np

_BACKEND = None


def _normalize(v):
    v = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


class _DlibBackend:
    """Thin, behaviour-preserving wrapper around face_recognition (dlib)."""
    name = "dlib"

    def __init__(self):
        import face_recognition
        self._fr = face_recognition

    def locate(self, rgb_frame, model=None):
        if model:
            return self._fr.face_locations(rgb_frame, model=model)
        return self._fr.face_locations(rgb_frame)

    def encode(self, rgb_frame, known_face_locations=None, num_jitters=2):
        return self._fr.face_encodings(
            rgb_frame, known_face_locations=known_face_locations,
            num_jitters=num_jitters)

    def distance(self, stored_embedding, face_embedding):
        # Preserves the exact call the matcher used: L2 distance in 128-D space.
        return float(self._fr.face_distance([stored_embedding], face_embedding)[0])

    def match_params(self):
        # dlib-calibrated cutoffs matching the original identify_student logic.
        return {"metric": "l2", "max_distance": 0.5}


class _InsightFaceBackend:
    """ArcFace buffalo_l (512-D). Detection + embedding happen together, so
    locate() runs the model once and caches faces for the following encode()."""
    name = "insightface"

    def __init__(self, det_size=640, ctx_id=0):
        from insightface.app import FaceAnalysis  # lazy: only needed if selected
        self._app = FaceAnalysis(name="buffalo_l")
        self._app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))
        self._cache = None  # (frame_array, faces)
        logging.info("InsightFace ArcFace buffalo_l backend loaded")

    def _faces(self, rgb_frame):
        # Cache by object *identity* (is), not id(): CPython recycles id() for
        # freed arrays, so an id() key could match a different, later frame and
        # return stale detections. Holding the array reference here also keeps
        # it alive, so a distinct frame can never reuse its identity.
        if self._cache is None or self._cache[0] is not rgb_frame:
            # insightface expects BGR; caller passes RGB (dlib convention).
            self._cache = (rgb_frame, self._app.get(rgb_frame[:, :, ::-1]))
        return self._cache[1]

    def locate(self, rgb_frame, model=None):
        # Return dlib-style (top, right, bottom, left) boxes for API parity.
        boxes = []
        for f in self._faces(rgb_frame):
            x1, y1, x2, y2 = [int(v) for v in f.bbox]
            boxes.append((y1, x2, y2, x1))
        return boxes

    def encode(self, rgb_frame, known_face_locations=None, num_jitters=2):
        # num_jitters is dlib-specific and ignored here.
        return [np.asarray(f.embedding, dtype=np.float32)
                for f in self._faces(rgb_frame)]

    def distance(self, stored_embedding, face_embedding):
        # Cosine *distance* (1 - cos sim) so "smaller = closer" matches dlib's
        # sense; match_params exposes the ArcFace cutoff.
        return 1.0 - float(np.dot(_normalize(stored_embedding), _normalize(face_embedding)))

    def match_params(self):
        # ArcFace cosine-distance cutoff; ~0.68 distance == ~0.32 cosine sim,
        # a common buffalo_l verification operating point. Tune per deployment.
        return {"metric": "cosine", "max_distance": 0.68}


def get_face_backend():
    """Return the process-wide face backend, honoring config.face_model()."""
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    try:
        import config as cf
        choice = cf.face_model()
    except Exception:
        choice = "dlib"
    if choice == "insightface":
        try:
            _BACKEND = _InsightFaceBackend()
            return _BACKEND
        except Exception as e:
            logging.error("InsightFace backend unavailable (%s); falling back to dlib. "
                          "Install with `pip install insightface onnxruntime-gpu`.", e)
    _BACKEND = _DlibBackend()
    return _BACKEND


_NAMED = {}


def get_backend_by_name(name):
    """Explicit backend, independent of config and of get_face_backend()'s
    cache. Enrollment dual-writes with BOTH backends (ArcFace for the
    forward-looking gallery, dlib for the deployed 128-D live matcher)
    regardless of which one the matcher is configured to use."""
    if name in _NAMED:
        return _NAMED[name]
    backend = _InsightFaceBackend() if name == "insightface" else _DlibBackend()
    _NAMED[name] = backend
    return backend
