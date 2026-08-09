"""Pure per-window reducers for the metrics export/synthesis paths.

Kept import-light (stdlib only) so the windowing math is unit-testable without
Flask/SQLAlchemy, and so the two utility.py call sites (CSV export and
synthesis) share ONE implementation instead of drifting copies.
"""
from collections import Counter


def reduce_video_window(facial_emotion, object_on_focus, attention_level,
                        windowsize, window_count):
    """Collapse one window's raw video samples into
    (most_common_emotion, most_common_object, avg_attention, attention_rate).

    An empty window has no attention data, so avg_attention is None (NOT 0 —
    the two utility.py copies disagreed here; 0 falsely reads as "measured
    zero attention"). attention_rate stays 0 for an empty window.
    """
    most_common_emotion = Counter(facial_emotion).most_common(1)[0][0] if facial_emotion else None
    most_common_object = Counter(object_on_focus).most_common(1)[0][0] if object_on_focus else None
    if attention_level:
        avg_attention = sum(attention_level) // len(attention_level)
        attention_rate = avg_attention / (windowsize * (window_count + 1))
    else:
        avg_attention = None
        attention_rate = 0
    return most_common_emotion, most_common_object, avg_attention, attention_rate
