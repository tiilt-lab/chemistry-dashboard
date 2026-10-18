"""A post-hoc audio run stages every utterance it processes and never wipes
the previous rows for nothing (src/audio_processing/processor_posthoc.py).
On 2026-10-18 the branch that takes the connector's own speaker name (MOSS)
skipped the staging step: 1,129 named turns were scored and dropped, the
publish wiped the pod's rows and posted none."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = open(os.path.join(ROOT, "src", "audio_processing", "processor_posthoc.py")).read()


def _body(name):
    start = SRC.index("    def %s(" % name)
    rest = SRC[start + 4:]
    m = re.search(r"\n    def ", rest)
    return rest[:m.start()] if m else rest


def test_a_turn_named_by_the_connector_is_staged_like_a_print_matched_one():
    body = _body("process_transcript")
    i = body.index("named_by_asr = bool(getattr(transcript_data, 'named_by_asr', False))")
    branch = body[i:body.index("            else:\n                if self.config.diarization:", i)]
    # one condition covers both ways of naming, and the staging call sits inside it
    assert "if named_by_asr or (self.config.diarization and self.fingerprints and len(self.fingerprints)):" in branch
    assert branch.count("self._staging.add(start_time, 'metrics'") == 1
    assert "checkFingerprints(" in branch and "if named_by_asr:" in branch
    # the staging is not conditional on the print check alone
    assert "elif self.config.diarization" not in branch


def test_a_completed_run_with_nothing_staged_is_abandoned_not_published():
    body = _body("__complete_callback")
    guard = body.index("if failure is None and len(self._staging) == 0:")
    assert guard < body.index("self._publish()")
    assert "nothing to publish" in body[guard:guard + 300]
