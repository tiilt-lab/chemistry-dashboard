"""Exactly-once completion accounting shared by the audio processors.

The live and post-hoc audio processors both spawn one worker thread per
utterance while a reader thread drains the ASR queue. Completion (post speaker
taggings / notify the client) must happen exactly once, after BOTH:
  - the reader has seen end-of-stream (mark_asr_complete), AND
  - every spawned worker has finished (running count back to 0).

Whichever of those two becomes true last must fire the callback, and it must
fire only once. This was hand-rolled identically in both processors; the
post-hoc copy drifted to an unlocked decrement that bypassed the latch,
re-introducing the very race the latch existed to prevent. This is that state
machine, in one place, with no heavy imports so it is unit-testable in CI.
"""
import threading


class CompletionLatch:
    def __init__(self, on_complete):
        self._on_complete = on_complete
        self._lock = threading.Lock()
        self._running = 0
        self._asr_complete = False
        self._completed = False

    def task_started(self):
        """A worker thread was spawned for one utterance."""
        with self._lock:
            self._running += 1

    def task_done(self):
        """A worker thread finished; complete if it was the last one and the
        reader has already ended the stream."""
        with self._lock:
            self._running -= 1
        self._maybe_complete()

    def mark_asr_complete(self):
        """The reader saw end-of-stream; complete if all workers have drained."""
        with self._lock:
            self._asr_complete = True
        self._maybe_complete()

    def _maybe_complete(self):
        with self._lock:
            if not self._asr_complete or self._running != 0 or self._completed:
                return
            self._completed = True
        # Outside the lock: the callback does real work (clustering, POSTs) and
        # must not be holding the accounting lock while it runs.
        self._on_complete()
