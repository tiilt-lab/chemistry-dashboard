"""CrisperWhisper 2.0 connectors (verbatim ASR with crisp word timestamps).

CrisperWhisper (nyra health) is a Whisper fine-tune that transcribes
*verbatim* — fillers, stutters, false starts — with word timestamps accurate
enough to measure pauses, which regular Whisper glues onto neighboring
words. Weights are non-commercial-research licensed; inference code is MIT.

The package needs its own CTranslate2 fork, so it lives in src/venv-crisper
and all inference goes through crisper_worker.py subprocesses:
  - CrisperWhisperASR (live): persistent --serve worker, one job per
    12-second window; the model stays loaded between windows.
  - CrisperWhisperPosthocASR: --oneshot on the whole recording, then emits
    gap-segmented Google-shaped AsrResults (same contract as Qwen3ASR;
    speaker attribution happens downstream via fingerprint matching).
"""
import json
import logging
import os
import queue as queue_module
import subprocess
import sys
import tempfile
import threading
import wave

from .base_asr import BaseASR, AsrResult

_WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crisper_worker.py")

DEFAULT_MODEL = "nyralabs/CrisperWhisper2.0_large"


def _worker_python():
    dedicated = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "venv-crisper", "bin", "python")
    return dedicated if os.path.exists(dedicated) else sys.executable


def _split_segments(words, max_gap=1.0, max_len=15.0):
    """Group a flat word list into utterance-ish segments on silent gaps.

    CrisperWhisper's word ends are actual speech ends (pauses aren't glued
    onto words), so gap-splitting gives natural utterance boundaries.
    words: [[text, start_s, end_s], ...] -> list of word-lists.
    """
    segments = []
    current = []
    for w in words:
        if current and (w[1] - current[-1][2] > max_gap or w[2] - current[0][1] > max_len):
            segments.append(current)
            current = []
        current.append(w)
    if current:
        segments.append(current)
    return segments


def _emit_segments(transcript_queue, words, offset=0.0):
    for seg in _split_segments(words):
        text = " ".join(w[0].strip() for w in seg).strip()
        triples = [(w[0].strip(), offset + w[1], offset + w[2]) for w in seg]
        if text and triples:
            transcript_queue.put(AsrResult(text, triples))


class CrisperWhisperASR(BaseASR):
    """Live connector: fixed windows against a persistent worker process."""

    WINDOW_SECONDS = 12.0

    def __init__(self, audio_queue, transcript_queue, config, media_type, interval):
        super().__init__(audio_queue, transcript_queue, config, media_type, interval)
        self._proc = None
        self._buffer = bytearray()
        self._window_start = 0.0

    def _spawn_worker(self):
        import config as cf
        model = cf.crisperwhisper_model()
        mode = cf.crisperwhisper_mode()
        logging.info("Starting CrisperWhisper worker (model=%s, mode=%s)", model, mode)
        self._proc = subprocess.Popen(
            [_worker_python(), _WORKER, "--serve", "--model", model, "--mode", mode],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1)
        ready = self._proc.stdout.readline()
        if not ready or not json.loads(ready).get("ready"):
            raise RuntimeError("CrisperWhisper worker failed to start")

    def start(self):
        self.running = True
        self._spawn_worker()
        self.asr_thread = threading.Thread(target=self._processing, name="crisper-asr")
        self.asr_thread.daemon = True
        self.asr_thread.start()

    def stop(self):
        self.running = False
        proc, self._proc = self._proc, None
        if proc:
            try:
                proc.stdin.write(json.dumps({"exit": True}) + "\n")
                proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def _window_full(self):
        samples = len(self._buffer) / self.DEPTH
        return samples / self.SAMPLE_RATE >= self.WINDOW_SECONDS

    def _processing(self):
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except queue_module.Empty:
                continue
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break
            self._buffer.extend(chunk)
            if self._window_full():
                self._flush()
        self._flush()
        self.transcript_queue.put(None)
        # The audio server ends a session by closing the stream, not by
        # calling stop() — without this, every finished session leaks a
        # ~4GB-GPU worker process.
        self.stop()

    def _ask_worker(self, wav_path):
        if self._proc is None or self._proc.poll() is not None:
            logging.warning("CrisperWhisper worker died — restarting")
            self._spawn_worker()
        self._proc.stdin.write(json.dumps({"audio": wav_path}) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("CrisperWhisper worker closed its pipe")
        return json.loads(line)

    def _flush(self):
        if len(self._buffer) < self.DEPTH:
            return
        window_len = (len(self._buffer) / self.DEPTH) / self.SAMPLE_RATE
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            with wave.open(tmp.name, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.DEPTH)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(bytes(self._buffer))
            data = self._ask_worker(tmp.name)
            if data.get("error"):
                logging.warning("CrisperWhisper window failed: %s", data["error"])
            else:
                _emit_segments(self.transcript_queue, data.get("words", []),
                               offset=self._window_start)
        except Exception as e:
            logging.warning("CrisperWhisper transcription failed: %s", e)
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass
        self._window_start += window_len
        self._buffer = bytearray()


class CrisperWhisperPosthocASR:
    """Post-hoc connector: one-shot worker over the whole recording."""

    def __init__(self, audio_queue, transcript_queue, config, media_type,
                 interval, audio_file=None, model_id=None, mode=None):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.audio_file = audio_file
        self.model_id = model_id or DEFAULT_MODEL
        self.mode = mode or "verbatim"
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._drain_queue, daemon=True,
                         name="crisper-queue-drain").start()
        threading.Thread(target=self._transcribe_file, daemon=True,
                         name="crisper-transcribe").start()

    def stop(self):
        self.running = False

    def _drain_queue(self):
        while self.running:
            try:
                chunk = self.audio_queue.get(timeout=0.25)
            except queue_module.Empty:
                continue
            if chunk is None or not isinstance(chunk, (bytes, bytearray)):
                break

    def _transcribe_file(self):
        try:
            logging.info("CrisperWhisper: transcribing %s via %s (mode=%s)",
                         self.audio_file, self.model_id, self.mode)
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
                out_path = tf.name
            try:
                proc = subprocess.run(
                    [_worker_python(), _WORKER,
                     "--oneshot", self.audio_file, out_path,
                     "--model", self.model_id, "--mode", self.mode],
                    capture_output=True, timeout=7200)
                if proc.returncode != 0:
                    raise RuntimeError("worker failed: %s" % proc.stderr.decode()[-500:])
                with open(out_path) as f:
                    data = json.load(f)
            finally:
                try:
                    os.remove(out_path)
                except OSError:
                    pass
            words = data.get("words", [])
            logging.info("CrisperWhisper: %d words", len(words))
            _emit_segments(self.transcript_queue, words)
        except Exception as e:
            logging.error("CrisperWhisper transcription failed: %s", e, exc_info=True)
        finally:
            self.running = False
            self.transcript_queue.put(None)
