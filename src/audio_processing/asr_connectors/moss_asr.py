"""MOSS-Transcribe-Diarize post-hoc connector: the default post-hoc engine.

One model (OpenMOSS 0.9B, Apache-2.0) listens to the whole recording and
writes timestamped, speaker-labelled, punctuated turns, so there is no
separate diarizer, aligner or word-assignment step. Its speaker labels are
anonymous (S01, S02, ...); they are named with moss_naming, the rules the
bake-off wrote (2026-10-18, Group 7: 94% of speech named on both laptops):
the enrolment print where a student has one, else a print cut from the
student's confidently named live rows on this recording, both laptops'
rosters, floors per print kind, a margin, the side from the prints or the
live rows, and elimination for a single printless student. Each turn goes to
the consumer as one AsrResult carrying the name (None when no print won) and
the naming confidence, flagged ``named_by_asr`` so the processor keeps them.
See README "MOSS end to end".
"""
import logging
import threading

import numpy as np

from .base_asr import AsrResult, PosthocFileASR
from .moss_run import DEFAULT_MAX_NEW_TOKENS, run_moss
from . import moss_naming


def _read_audio(path):
    """(float32 mono samples, sample rate) of the recording."""
    import soundfile
    audio, sr = soundfile.read(path, dtype="float32", always_2d=False)
    if getattr(audio, "ndim", 1) > 1:
        audio = audio[:, 0]
    return np.ascontiguousarray(audio), int(sr)


def _embedder(speaker_model):
    """signal -> unit vector with the service's ECAPA model (float domain)."""
    from .cluster_reconcile import _embed_float

    def embed(sig):
        return moss_naming.unit(_embed_float(np.asarray(sig, dtype=np.float32), speaker_model))
    return embed


def _percent(sim, margin):
    """The 0-100 confidence the transcript panel shows, on the live scale."""
    try:
        from speaker_diarization import pyDiarization as pyd
        return pyd.confidence_percent(sim, margin)
    except Exception:
        return int(round(max(0.0, min(1.0, float(sim))) * 100))


def _enrolment_print(alias, speaker_model):
    try:
        from speaker_diarization import pyDiarization as pyd
        emb = pyd._print_embedding(alias, None, speaker_model)
    except Exception as e:
        logging.debug("MOSS naming: no enrolment print for %s: %s", alias, e)
        return None
    return moss_naming.unit(emb) if emb is not None else None


class MossASR(PosthocFileASR):
    DRAIN_NAME = "moss"
    NAME = "moss"

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval, audio_file,
                 hotwords=None, enrolled=None, speaker_model=None, max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
                 roster=None, naming_rows=None):
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
        # The pod's own roster (every alias, printed or not); the partner's
        # comes with the naming rows. ``naming_rows`` given = no API call.
        self.roster = [str(a) for a in (roster or []) if a]
        if not self.roster and isinstance(enrolled, dict):
            self.roster = [str(v.get("alias")) for v in enrolled.values() if v.get("alias")]
        elif not self.roster and enrolled:
            self.roster = [str(a) for a in enrolled]
        self.naming_rows = naming_rows
        self.running = False
        self.diarizer_used = None
        self.lock = threading.Lock()

    def _fetch_naming_rows(self):
        if self.naming_rows is not None:
            return self.naming_rows
        key = getattr(self.config, "auth_key", None)
        if not key:
            return None
        try:
            import callbacks
            return callbacks.get_naming_rows(key)
        except Exception as e:
            logging.info("MOSS naming: rows lookup failed: %s", e)
            return None

    def _name_turns(self, turns):
        """{cluster: record} from moss_naming, or {} when nothing can be named."""
        if self.speaker_model is None or not turns:
            return {}
        rows_doc = self._fetch_naming_rows() or {}
        roster = {a: "own" for a in self.roster}
        for a in rows_doc.get("partner_speakers") or []:
            roster.setdefault(str(a), "far")
        if not roster:
            return {}
        audio, sr = _read_audio(self.audio_file)
        embed = _embedder(self.speaker_model)
        import recording_sidecar
        clock = {"start_offset": float(getattr(self.config, "start_offset", 0.0) or 0.0),
                 "moves": list(getattr(self.config, "clock_moves", None) or [])}
        to_rec = lambda session_t: recording_sidecar.recording_time(clock, session_t)     # noqa: E731
        to_session = lambda rec_t: recording_sidecar.session_time(clock, rec_t)           # noqa: E731
        prints, kinds = {}, {}
        for alias in roster:
            vec = _enrolment_print(alias, self.speaker_model)
            if vec is not None:
                prints[alias], kinds[alias] = vec, "enrolment"
        rows = rows_doc.get("rows") or []
        made = moss_naming.session_prints(audio, sr, to_rec, rows, embed, wanted={a for a in roster if a not in prints})
        for alias, (vec, seconds) in made.items():
            prints[alias], kinds[alias] = vec, "session"
        logging.info("MOSS naming: prints %s; no print: %s",
                     {a: (kinds[a] + (" %ss" % made[a][1] if a in made else "")) for a in prints},
                     [a for a in roster if a not in prints])
        own_id = rows_doc.get("device")
        live_own = [r for r in rows if own_id is None or r.get("device") == own_id]
        return moss_naming.name_clusters(audio, sr, turns, roster, prints, kinds, live_own, to_session, embed), roster

    def _transcribe_file(self):
        try:
            result = run_moss(self.audio_file, hotwords=self.hotwords, max_new_tokens=self.max_new_tokens,
                              handle=getattr(self, "worker", None))
            turns = result["turns"]
            self.diarizer_used = "moss"
            named, roster = {}, {}
            try:
                out = self._name_turns(turns)
                if out:
                    named, roster = out
            except Exception as e:  # noqa: BLE001 - naming is a bonus; the transcript still goes out
                logging.warning("MOSS naming failed; turns stay unnamed: %s", e, exc_info=True)
            clusters = {t["speaker"] for t in turns}
            logging.info("MOSS: %d of %d speakers named (%s)", sum(1 for c in named.values() if c.get("name")), len(clusters),
                         ", ".join("%s=%s" % (c, v.get("name") or ("?" + str(v.get("guess")))) for c, v in sorted(named.items())))
            emitted = 0
            for t in turns:
                text = (t.get("text") or "").strip()
                if not text or not self.running:
                    continue
                asr_result = AsrResult(text, [(text, float(t["start"]), float(t["end"]))])
                record = named.get(t["speaker"])
                if record is not None:
                    name, conf = moss_naming.turn_attribution(record, roster)
                    conf["cluster"] = t["speaker"]
                    if name and conf.get("sim") is not None:
                        conf["percent"] = _percent(conf["sim"], conf.get("margin") or 0.0)
                    asr_result.speaker_tag, asr_result.speaker_confidence = name, conf
                else:
                    asr_result.speaker_tag, asr_result.speaker_confidence = None, {"cluster": t["speaker"]}
                asr_result.named_by_asr = True
                self.transcript_queue.put(asr_result)
                emitted += 1
            logging.info("MOSS: emitted %d transcript results", emitted)
        except Exception as e:
            logging.error("MOSS transcription failed: %s", e, exc_info=True)
            self.fail(e)
        finally:
            self.running = False
            self.transcript_queue.put(None)
