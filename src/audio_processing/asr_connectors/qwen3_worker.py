"""Qwen3-ASR subprocess worker (runs in the python3.10 qwen_venv).

The qwen-asr package needs Python >=3.10 while the audio pipeline runs 3.9,
so the connector shells out to this script. Input: a wav path. Output: one
JSON document on stdout: {"segments": [{"text", "words": [[w, start, end]]}]}.

Words come from Qwen3-ForcedAligner; they are grouped into utterance segments
on sentence-ending punctuation or a silence gap, matching the granularity the
dashboard stores per transcript row.
"""

import sys
import json

GAP_SECONDS = 1.0
MAX_SEGMENT_SECONDS = 30.0


def main():
    wav = sys.argv[1]
    model_id = sys.argv[2] if len(sys.argv) > 2 else "Qwen/Qwen3-ASR-1.7B"
    from qwen_asr import Qwen3ASRModel

    model = Qwen3ASRModel.from_pretrained(
        model_id,
        forced_aligner="Qwen/Qwen3-ForcedAligner-0.6B",
        dtype="bfloat16",
        device_map="cuda:0",
    )
    result = model.transcribe(audio=wav, return_time_stamps=True)
    r = result[0] if isinstance(result, list) else result
    items = list(getattr(r, "time_stamps", None) or [])

    segments = []
    current = {"words": []}

    def flush():
        if current["words"]:
            segments.append({
                "text": " ".join(w[0] for w in current["words"]),
                "words": current["words"],
            })
            current["words"] = []

    prev_end = None
    seg_start = None
    for item in items:
        word, start, end = item.text, float(item.start_time), float(item.end_time)
        if current["words"] and (
            (prev_end is not None and start - prev_end > GAP_SECONDS)
            or (seg_start is not None and end - seg_start > MAX_SEGMENT_SECONDS)
        ):
            flush()
        if not current["words"]:
            seg_start = start
        current["words"].append([word, start, end])
        prev_end = end
        if word and word[-1] in ".?!":
            flush()
    flush()

    json.dump({"segments": segments, "text": getattr(r, "text", "")}, sys.stdout)


if __name__ == "__main__":
    main()
