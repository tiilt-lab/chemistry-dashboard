"""CrisperWhisper 2.0 worker — runs inside src/venv-crisper.

The crisperwhisper package ships its own CTranslate2 fork
(ctranslate2-crisperwhisper) whose import would shadow the real ctranslate2
that faster-whisper/WhisperX depend on, so it lives in a dedicated venv and
this worker is the only thing that imports it (same isolation pattern as
sortformer_cli / qwen3_worker).

Two modes:
  --oneshot AUDIO OUT.json   transcribe one file, write JSON, exit (post-hoc)
  --serve                    JSON-lines loop on stdin/stdout for the live
                             connector: {"audio": path} in, one result line
                             out per job. Prints {"ready": true} after the
                             model loads. Model loads once (~7s), then ~20x
                             realtime on GPU.

Output shape (both modes): {"text": str, "words": [[word, start_s, end_s], ...]}
"""
import argparse
import json
import sys


def _load_model(model_id, compute_type):
    from crisperwhisper import CrisperWhisperModel
    return CrisperWhisperModel(model_id, compute_type=compute_type)


def _transcribe(model, audio_path, language, mode):
    result = model.transcribe(
        audio_path, language=language, mode=mode, word_timestamps=True
    )
    words = [
        [w.word, round(float(w.start), 3), round(float(w.end), 3)]
        for w in (result.words or [])
    ]
    return {"text": result.text or "", "words": words}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--oneshot", nargs=2, metavar=("AUDIO", "OUT"))
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--model", default="nyralabs/CrisperWhisper2.0_large")
    parser.add_argument("--mode", default="verbatim")
    parser.add_argument("--language", default="en")
    parser.add_argument("--compute-type", default="float16")
    args = parser.parse_args()

    model = _load_model(args.model, args.compute_type)

    if args.oneshot:
        audio, out = args.oneshot
        data = _transcribe(model, audio, args.language, args.mode)
        with open(out, "w") as f:
            json.dump(data, f)
        return

    if args.serve:
        print(json.dumps({"ready": True}), flush=True)
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                job = json.loads(line)
                if job.get("exit"):
                    break
                data = _transcribe(
                    model,
                    job["audio"],
                    job.get("language", args.language),
                    job.get("mode", args.mode),
                )
            except Exception as e:  # one bad window must not kill the loop
                data = {"error": str(e)}
            print(json.dumps(data), flush=True)


if __name__ == "__main__":
    main()
