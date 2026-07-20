"""Contract tests: catch producer/consumer drift that unit tests miss.

The live attention-analytics ValueError (6-tuple produced, 7-tuple unpacked)
was exactly this kind of silent mismatch. These tests read the source and
assert the shapes line up, so a future edit to one side fails CI.
"""
import os
import re

SRC = os.path.join(os.path.dirname(__file__), "..", "src")


def _read(*parts):
    with open(os.path.join(SRC, *parts)) as f:
        return f.read()


def test_video_analytics_payload_arity_matches_consumer():
    # Consumer unpacks a fixed-arity tuple in detect.py.
    detect = _read("video_processing", "attention_tracking", "detect.py")
    m = re.search(r"images,facial_embeddings,batch_track,time_marker,"
                  r"vid_img_dir,auth_key,last_batch = payload", detect)
    assert m, "detect.py worker unpack signature changed; update this contract"
    consumer_arity = 7

    # Both producers (live + posthoc) must build the same arity.
    live = _read("video_processing", "video_cartoonizer", "videoprocessor.py")
    posthoc = _read("video_processing", "video_cartoonizer",
                    "videoprocessor_posthoc.py")
    for name, text in [("live", live), ("posthoc", posthoc)]:
        for lst in re.findall(r"payload = \[(.*?)\]", text, re.DOTALL):
            # only the frame-analytics payloads (they carry facialEmbeddings)
            if "facialEmbeddings" not in lst:
                continue
            arity = len([x for x in lst.split(",") if x.strip()])
            assert arity == consumer_arity, (
                "%s producer builds a %d-tuple; detect.py unpacks %d"
                % (name, arity, consumer_arity))


def test_provenance_registry_covers_frontend_fields():
    # The frontend resolves per-pod labels via MODULE_TO_PROVENANCE fields;
    # the API registry must contain every field the frontend asks for.
    backend = _read("server", "routes", "callback.py")
    reg = re.search(r"_PROVENANCE_REGISTRY = \{(.*?)\n\}", backend, re.DOTALL)
    assert reg, "provenance registry not found"
    backend_fields = set(re.findall(r'"(\w+)":', reg.group(1)))

    fe_path = os.path.join(SRC, "..", "frontend", "src", "components",
                           "infographics-view", "infographics-comparison.jsx")
    with open(fe_path) as f:
        fe = f.read()
    mod = re.search(r"MODULE_TO_PROVENANCE = \{(.*?)\}", fe, re.DOTALL)
    assert mod, "MODULE_TO_PROVENANCE not found in frontend"
    frontend_fields = set(re.findall(r':\s*"(\w+)"', mod.group(1)))

    missing = frontend_fields - backend_fields
    assert not missing, (
        "frontend references provenance fields the API registry lacks: %s"
        % missing)
