"""The post-or-not decision shared by VideoMetricProcessor.worker.

VideoMetricProcessor had two near-identical methods, ``worker`` and
``worker_posthoc``, differing ONLY in whether metrics get posted:
``worker`` gated on ``video_metrics and source in {real_time, post_hoc}``;
``worker_posthoc`` hardcoded ``can_post = True``. Since worker_posthoc was only
ever driven with source="post_hoc", the two were behavior-identical. The fork
is collapsed to one ``worker(payload, post_always=False)`` whose decision lives
in this pure, import-light policy (VideoMetricProcessor itself pulls in
torch/cv2/ultralytics and can't load in CI).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src",
                                "video_processing", "video_cartoonizer"))

from metric_post_policy import should_post_metrics  # noqa: E402


def test_no_metrics_never_posts():
    assert should_post_metrics({}, "post_hoc", post_always=True) is False
    assert should_post_metrics(None, "real_time") is False


def test_live_worker_posts_for_realtime_and_posthoc_sources():
    m = {"p": [[0, "neutral", 1, "screen"]]}
    assert should_post_metrics(m, "real_time") is True
    assert should_post_metrics(m, "post_hoc") is True


def test_live_worker_does_not_post_for_unknown_source():
    # Preserves worker's original guard: an unrecognized source stays silent.
    m = {"p": [[0, "neutral", 1, "screen"]]}
    assert should_post_metrics(m, "batch_reprocess") is False


def test_post_always_matches_old_worker_posthoc_true_branch():
    # worker_posthoc set can_post=True regardless of source -> post_always=True
    # posts whenever there are metrics, for ANY source.
    m = {"p": [[0, "neutral", 1, "screen"]]}
    assert should_post_metrics(m, "batch_reprocess", post_always=True) is True
    assert should_post_metrics(m, "post_hoc", post_always=True) is True


def test_worker_posthoc_fork_is_removed():
    # The duplicated method must be gone and the single worker must route its
    # decision through the shared policy (not a hardcoded can_post).
    base = os.path.join(os.path.dirname(__file__), "..", "src",
                        "video_processing", "video_cartoonizer")
    with open(os.path.join(base, "VideoMetricProcessor.py")) as f:
        proc = f.read()
    assert "def worker_posthoc" not in proc, "worker_posthoc fork must be deleted"
    assert "should_post_metrics(" in proc, "worker must use the shared policy"
    with open(os.path.join(base, "videoprocessor_posthoc.py")) as f:
        caller = f.read()
    assert "video_metric_analytics.worker_posthoc" not in caller, \
        "posthoc caller must use worker(..., post_always=True)"
