"""The frame payload passed from the video processors to the detect worker.

The worker unpacks exactly 7 elements, in this order. It was hand-built as a
list literal at four call sites (live + three post-hoc), each with a comment
warning that the order must not drift (omitting the trailing last_batch once
raised "not enough values to unpack" and silently disabled live analytics).
Build it here so there is one definition of that contract.
"""


def build_frame_payload(frames, facial_embeddings, batch_track, time_markers,
                        vid_img_dir, auth_key, last_batch):
    """last_batch is False for the live stream (no natural final batch;
    teardown is driven by disconnect) and True on the post-hoc final flush."""
    return [frames, facial_embeddings, batch_track, time_markers,
            vid_img_dir, auth_key, last_batch]
