"""Whether a batch of computed video metrics should be posted to the server.

Extracted so the single VideoMetricProcessor.worker (previously forked into
worker/worker_posthoc that differed only here) has one decision, and so it can
be unit-tested without importing torch/cv2/ultralytics.
"""


def should_post_metrics(video_metrics, source, post_always=False):
    """True iff this batch should be POSTed.

    - No metrics -> never post (nothing to send).
    - ``post_always`` (the old worker_posthoc path): post whenever there are
      metrics, regardless of source.
    - Otherwise (the live/queue path): post only for recognized sources.
    """
    if not video_metrics:
        return False
    if post_always:
        return True
    return source in ("real_time", "post_hoc")
