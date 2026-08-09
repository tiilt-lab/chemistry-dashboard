"""The 7-element frame payload the detect worker unpacks.

videoprocessor.py (live) and videoprocessor_posthoc.py built this list at four
sites, with a comment at each warning the order must stay in lockstep with the
worker's 7-tuple unpack (omitting the last element once silently disabled live
gaze/attention analytics with a ValueError). One builder, one order.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "video_processing", "video_cartoonizer"))

from frame_payload import build_frame_payload  # noqa: E402


def test_payload_order_and_arity():
    p = build_frame_payload("frames", "emb", 3, "marks", "/imgs", "auth-1", True)
    assert p == ["frames", "emb", 3, "marks", "/imgs", "auth-1", True]
    assert len(p) == 7  # the worker unpacks exactly 7


def test_last_batch_flag_carried():
    assert build_frame_payload(1, 2, 3, 4, 5, 6, False)[6] is False
    assert build_frame_payload(1, 2, 3, 4, 5, 6, True)[6] is True
