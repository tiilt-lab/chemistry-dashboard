"""MOSS-Transcribe-Diarize post-hoc connector: the default post-hoc engine.

One model (OpenMOSS 0.9B, Apache-2.0) listens to the whole recording and
writes timestamped, speaker-labelled, punctuated turns, so there is no
separate diarizer, aligner or word-assignment step. Its speaker labels are
anonymous (S01, S02, ...); they are named against the enrolled voice prints
with the same reconciliation the external diarizers use, and each turn goes
to the consumer as one AsrResult carrying the name (or the label when no
print matched) as ``speaker_tag``.

Measured on the Viking class (2026-10-18, Group 7, both laptops): 94% of
speech named on both laptops, 19 unnamed merged lines against 50-71 for the
other engines, punctuation and no doubled words; cross-laptop agreement 83%,
a little under the diarizer + recognizer pairs. See README "MOSS end to end".
"""
import logging
import threading

from .base_asr import AsrResult, PosthocFileASR
from .moss_run import DEFAULT_MAX_NEW_TOKENS, run_moss


class MossASR(PosthocFileASR):
    DRAIN_NAME = "moss"
    NAME = "moss"

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval, audio_file,
                 hotwords=None, enrolled=None, speaker_model=None, max_new_tokens=DEFAULT_MAX_NEW_TOKENS):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.media_type = media_type
        self.interval = interval
        self.audio_file = audio_file
        self.hotwords = [h for h in (hotwords or []) if h]
        self.enrolled = enrolled
        self.speaker_model = speaker_model
        self.max_new_tokens = max_new_tokens
        self.running = False
        self.diarizer_used = None
        self.lock = threading.Lock()

    def _transcribe_file(self):
        try:
            result = run_moss(self.audio_file, hotwords=self.hotwords, max_new_tokens=self.max_new_tokens,
                              handle=getattr(self, "worker", None))
            turns = result["turns"]
            self.diarizer_used = "moss"
            cluster_map = {}
            if self.enrolled and self.speaker_model and turns:
                from .cluster_reconcile import build_cluster_to_enrolled_map
                cluster_map = build_cluster_to_enrolled_map(
                    self.audio_file, [(t["start"], t["end"], t["speaker"]) for t in turns],
                    self.enrolled, self.speaker_model)
                logging.info("MOSS: %d of %d speakers matched an enrolled voice", len(cluster_map), len({t["speaker"] for t in turns}))
            emitted = 0
            for t in turns:
                text = (t.get("text") or "").strip()
                if not text or not self.running:
                    continue
                asr_result = AsrResult(text, [(text, float(t["start"]), float(t["end"]))])
                asr_result.speaker_tag = cluster_map.get(t["speaker"], t["speaker"])
                self.transcript_queue.put(asr_result)
                emitted += 1
            logging.info("MOSS: emitted %d transcript results", emitted)
        except Exception as e:
            logging.error("MOSS transcription failed: %s", e, exc_info=True)
            self.fail(e)
        finally:
            self.running = False
            self.transcript_queue.put(None)
