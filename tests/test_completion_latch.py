"""Exactly-once completion for the audio processors.

Both AudioProcessor (live) and AudioProcessorPosthoc had the same hand-rolled
completion accounting: a lock, a running-process counter, an asr_complete flag,
and a _completed latch, so that whichever of {reader finishes, last worker
finishes} happens last fires the tagging/completion callback EXACTLY once.

The live processor did this correctly (decrement under lock -> _finish_if_done
with the latch). The posthoc processor had DRIFTED: it decremented unlocked and
called __complete_callback directly, bypassing the latch — the exact race the
latch was added to fix (a lost decrement, or a double-fired tagging POST).

CompletionLatch is that state machine, once, dependency-free (the processors
import torch/numpy/etc. and can't load in CI). These tests pin the
exactly-once contract, including under real thread contention.
"""
import os
import sys
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "audio_processing"))

from completion_latch import CompletionLatch  # noqa: E402


def _counter():
    calls = []
    return calls, (lambda: calls.append(1))


def test_no_completion_before_asr_complete():
    calls, cb = _counter()
    latch = CompletionLatch(cb)
    latch.task_started()
    latch.task_done()          # running back to 0, but asr not complete
    assert calls == []


def test_completes_when_asr_ends_after_workers_drain():
    calls, cb = _counter()
    latch = CompletionLatch(cb)
    latch.task_started()
    latch.task_done()
    latch.mark_asr_complete()  # reader finishes last -> fire now
    assert calls == [1]


def test_completes_when_last_worker_finishes_after_asr_end():
    calls, cb = _counter()
    latch = CompletionLatch(cb)
    latch.task_started()
    latch.task_started()
    latch.mark_asr_complete()  # asr done but 2 workers still running -> no fire
    assert calls == []
    latch.task_done()
    assert calls == []
    latch.task_done()          # last worker finishes -> fire
    assert calls == [1]


def test_fires_exactly_once_even_if_both_conditions_race():
    calls, cb = _counter()
    latch = CompletionLatch(cb)
    latch.task_started()
    latch.mark_asr_complete()  # asr done, 1 worker running
    latch.task_done()          # completes here
    # A late/duplicate signal must NOT fire a second callback.
    latch.mark_asr_complete()
    assert calls == [1]


def test_exactly_once_under_thread_contention():
    calls = []
    lock = threading.Lock()

    def cb():
        with lock:
            calls.append(1)

    latch = CompletionLatch(cb)
    N = 200
    for _ in range(N):
        latch.task_started()

    workers = [threading.Thread(target=latch.task_done) for _ in range(N)]
    reader = threading.Thread(target=latch.mark_asr_complete)
    threads = workers + [reader]
    # Interleave the reader among the workers to force the race.
    threads.insert(N // 2, threads.pop())
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls == [1], "completion callback must fire exactly once"
