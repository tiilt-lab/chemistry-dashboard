# Codebase antipattern sweep — round 2 (2026-08-09)

Fresh discovery pass over `main`, four parallel reviews (server+common, audio,
video, frontend). Round 1 (finished 2026-08-07) is fully shipped; nothing below
repeats it. Extra scrutiny went to code that landed after round 1: the
streaming analytics decoder (8e6b12c), throughput gauge (7760d13), the no-video
and lag alarms (2cec6c9, 761f5b1), the NME clustering rewrite (568d05b), and
the byod recorder churn (a99dfe6, 9016fe0, f46f817, f51c45d).

Every finding was verified against the code at the cited line; two were
reproduced live in `venv-unified`. Severity: **P1** = corrupts data / kills a
feature or run / security. **P2** = wrong results, degradation, or stranded UI
under real use. **P3** = hygiene / latent.

## STATUS (2026-08-09, same day): all P1s and all P2s are FIXED.

Commits: 10f26db (audio P1), be8e9c0 (server P1), f0d2850 (video P1),
fe64fa1 (frontend P1), then the P2 batches: server, audio, video, frontend
(one commit each — see git log for this date). Only the P3 tail below remains
open, plus these deliberately-accepted leftovers from the P2 round:

- **#14**: the (session_id, name) unique constraint now exists in
  `__table_args__` (fresh installs get it) and both TOCTOU joins converge in
  application code — but no Alembic migration was written for the live DB
  (the migration history has multiple heads; write it as its own careful
  task if the belt-and-braces DB constraint is wanted).
- **#18**: the session-video upload still runs ffmpeg synchronously on the
  request thread (now bounded by MAX_CONTENT_LENGTH + its 600s timeout);
  moving it to the posthoc queue is a P3-grade follow-up.
- **#26 (partial)**: the posthoc audio service still does its `.dat`→wav
  conversion and video-audio recovery on its own reactor during init — that
  reactor serves only trigger UIs, so it was left rather than restructure
  init into async. The live audio reactor was fully unblocked.

---

## P1

### Server

1. **Pod device-websocket DB calls run with no Flask app context — pod `auth`
   and the help button are silently dead** — `src/server/device_websockets.py:123-159`.
   Flask-SQLAlchemy 3.1.1 raises `RuntimeError` on `db.session` use outside a
   context; the `except Exception` at `onMessage` (line 109) mislabels it
   "Payload is not properly formatted JSON". Neighboring handlers
   (`add_connection`, `scheduled_tasks.py:13-15`) wrap correctly — `process_json`
   doesn't. Also `remove_connection` calls `database.close_session()` at :41
   *outside* its `with app.app_context()` (:38) — raises on every disconnect.
   Even once fixed, the DB work belongs off the reactor thread.

2. **Cross-tenant IDOR: any logged-in user (or API client) can delete any
   user's topic model** — `src/server/wrappers.py:204-216` +
   `src/server/routes/topic_model.py:82-94`. `verify_topic_model_access` does
   no `owner_id` filter (contrast `verify_keyword_list_access`); DELETE removes
   the row and the `topicModels/` file.

3. **One rater's rating silently overwrites another's** —
   `src/server/routes/student.py:242-245`. The existing-rating lookup passes
   `raterid=None`, so a second rater's submission updates the first rater's
   row. Research-data corruption with no trace.

### Audio (both reproduced in venv-unified)

4. **DOA is 100% dead under numpy 2.4.6** —
   `src/audio_processing/doa/doa_respeaker_v2_6mic_array.py:39` uses removed
   `np.fromstring`; the catch-all at :76-78 converts every call to `-1`, which
   is truthy, so `direction: -1` is persisted for every utterance of every
   6-mic pod while the pipeline reports success. Fix: `np.frombuffer`. Fix
   together with **#22** (gcc_phat NaN), which is currently masked by this.

5. **Google post-hoc ASR hangs forever on STOP** —
   `asr_connectors/google_asr_connector.py:110`: the STOP sentinel ends the
   generator but `processing()` (:189) loops and builds a new generator that
   blocks on an empty queue forever. `transcript_queue.put(None)` (:211) is
   unreachable → completion never fires, `running_audio_processes` pins the pod
   ("already running" forever) and the in-memory AudioBuffer with it
   (`server_posthoc.py:472-482`). Hit whenever posthoc selects the Google path.

### Video

6. **Live-analytics worker threads stop when the last client leaves and never
   restart** — `src/video_processing/server.py:726-730` calls `.stop()` at
   zero connections; the only `.start()`s are in `__main__` (:761-762). Within
   the 600s idle-recycle window a new class joins a live process whose
   analytics threads are gone: frames still enqueue (bounded ~5 GB/pod across
   the queue manager) but nothing drains; gaze/emotion/attention silently stop
   until systemd recycles. Related: live pods never send `last_batch=True`, so
   `frame_queue_manager`/`accumulator_queue_manager` entries never evict
   (`videoprocessor.py:334-341`, `detect.py:392-393`,
   `VideoMetricProcessor.py:87-88`).

7. **Decoder teardown can wedge the reactor permanently** (new in 8e6b12c) —
   `signal_end` → `VideoProcessor.stop()` → `vid_pro_thread.join()` with no
   timeout (`videoprocessor.py:128-130`), which waits on the decoder queue's
   SENTINEL. `_read_frames` (`server.py:231-279`) has no try/finally: an
   exception (including one thrown out of `self.sink(...)` at :255) kills the
   reader without the sentinel → consumer blocks forever → `join()` never
   returns → **the reactor is wedged and every pod stops being read**. Even the
   happy path blocks the reactor for seconds per disconnect (ffmpeg flush +
   in-flight batch). Fix: `try/finally: put(SENTINEL)` + join timeout.

### Frontend

8. **byod join page has no unmount teardown and no `beforeunload` guard** —
   `frontend/src/byod-join/byod-join-component.jsx` (only the small effects at
   :118/:269/:323/:413/:440/:637/:993 clean up; none touches sockets, recorder,
   or tracks; `navigateToLogin` :1873 guards only the in-app arrow).
   - Browser back mid-recording: JoinPage unmounts, but MediaRecorder, worklet,
     and both websockets keep streaming — silent capture from the landing page,
     pod still "live" for the instructor, camera light on until the tab dies.
   - Refresh/close mid-session: drops the current ≤10s chunk plus everything in
     `videows.bufferedAmount` — the congested-uplink backlog `flushAndDrainVideo`
     (:1435) exists to protect — with no prompt.
   Fix shape: unmount effect calling `disconnect(true)` with handler detach, +
   `beforeunload` while armed.

---

## P2

### Server

9. **`GET /sessions/<sid>/devices/<sdid>` 500s on every call** —
   `routes/session.py:713-721`: the view demands a `processing_key` positional
   that nothing supplies → `TypeError` always.

10. **`callback/tag` loses the embeddings-file assignment** —
    `routes/callback.py:339-343`: `session_device.embeddings = embeddingsFile`
    is never committed; teardown rolls it back every time. Related:
    `handlers/callback_handlers.py:15-16` indexes `results[i]` in lockstep with
    the transcripts query — any count mismatch raises IndexError or mis-tags.

11. **Unauthenticated synthesized-report endpoint recomputes + rewrites on
    every GET** — `routes/session.py:1310-1332`: no auth decorator, heavy
    recompute per request, DB write per request (amplification target);
    `AttributeError` at :1316 on unknown ids; check-then-add race duplicates
    report rows.

12. **Open LLM endpoints block Werkzeug workers up to 10 min** —
    `routes/llm_query.py:54-63, 140-156, 195-204`: `timeout=600` on the request
    path of unauthenticated routes; a few concurrent requests pin the whole
    threaded pool. Plus raw `KeyError` 500s on `retrieve_existing_report`
    (:156/:176) and `default_question_id` (:203).

13. **`image_queue_dict` unbounded + racy** — `routes/session.py:31,
    1356-1368, 1386-1410`: base64 frames accumulate for the process lifetime
    unless a browser opens the stream; unlocked check-then-set can drop a batch.

14. **`(session_id, name)` unique constraint is a no-op; BYOD join is
    check-then-insert** — `tables/session_device.py:32` (bare expression, not
    `__table_args__`; absent from migrations) + `database.py:731-758`. Two
    same-named pods can be created concurrently, then the re-join flow and
    `next_group_letter_name` pick the wrong one. Same TOCTOU in
    `generate_session_passcode` (`database.py:637-653`).

15. **Heart-rate ingest 500s on an empty alias/sensor, dropping up to 500
    samples** — `routes/session.py:855-857`: `sanitize('')` returns `None` →
    `None[:64]` TypeError outside the per-sample try; the `or 'Unknown'`
    fallback is after the slice and unreachable.

16. **Plain session rename 404s for users with no folders** —
    `routes/session.py:107-115`: `folder=None` passes `!= -1` and the
    first-folder-or-None lookup fails. Should be `folder is not None and
    folder != -1`.

17. **`get_student_longitudinal` N+1 fan-out on an open endpoint** —
    `database.py:1487-1586` (~5 queries + JSON parse per session appeared in),
    anonymously reachable (`routes/session.py:1012-1018`).

18. **Video upload: synchronous ffmpeg on the request thread, no
    `MAX_CONTENT_LENGTH`** — `routes/session.py:882-925` (up to 10 min);
    `_fixed_video_path` remux holds the per-device lock up to 300s/segment
    (:305-368).

### Audio

19. **`running_processes` counter unlocked across threads** —
    `processor.py:161, 324-326`, `processor_posthoc.py:220, 400-402`: a lost
    decrement means completion (and the OOM-preventing teardown at
    `server_posthoc.py:509-528`) never fires; the double-fire window duplicates
    the tagging POST. The class already has `_embeddings_lock`; the counter
    needs the same.

20. **Topic argmax never updates `max`** — `processor.py:207-211` +
    `processor_posthoc.py:274-278`: `topic_id` is the *last* topic with p>0,
    not the most probable; every stored topic is effectively arbitrary.
    (Verified in-file.)

21. **NME clustering runs on raw-int16-domain embeddings** —
    `speaker_diarization/pyDiarization.py:21-27` (`embedSignal`, no `/32768.0`)
    is the sole embedder for the no-fingerprint path (`processor.py:291`,
    `processor_posthoc.py:341`), while every other path was deliberately
    migrated to float and `MERGE_CENTROID_SIM = 0.45` (:356) was calibrated in
    float space. One-line fix.

22. **`gcc_phat` divides by zero on silent windows → NaN bearing** —
    `doa/gcc_phat.py:29` (reproduced with zero input). Currently masked by P1
    #4; fix together (epsilon floor / skip zero-energy).

23. **Embedding-file resume silently dead** — save as `dtype=object`
    (`processor.py:107`) but `np.load` without `allow_pickle=True`
    (`processor.py:282`, posthoc :332) — reproduced; every resume restarts with
    `[]`, dropping pre-reconnect utterances from clustering.

24. **`_PRINT_CACHE` / `_SESSION_ACC` never evict** —
    `pyDiarization.py:99-106` (+ `segment_split.py:52-56`): re-enrollment is
    ignored until restart; per-mic session adaptation leaks into the next day's
    session. Needs per-session scoping or invalidation on fingerprint set.

25. **`calculateNewness` NaN poisoning** — `speaker_metrics.py:126-135`: a
    near-duplicate utterance yields a zero-norm basis vector → NaN row is
    concatenated into `subspace_basis`, silently zeroing newness for the rest
    of the session. Guard the basis construction, not just the final division.

26. **Heavy synchronous work on the audio reactor thread** — enrollment blob
    processing (moviepy + ECAPA + cross-match) inside `onMessage`
    (`server.py:233-358`, `enrollment_check.py:137-209`); posthoc `.dat`→wav in
    memory (`server_posthoc.py:184-193`) and recovery ffmpeg `timeout=600`
    (:457-459); `WaveRecorder.close()` reads the whole session `.dat` into RAM
    and `np.reshape` aborts on a truncated final frame (`recorder.py:26-35`).

27. **Posthoc registry claim leaks on any exception between claim and start**
    — `server_posthoc.py:166-172` (missing enrollment wav at :204, `.dat`
    conversion, `signal_start`) → swallowed at :104-107 → pod permanently
    "already running". Only the `ProcessingConfig` branch releases (:179).
    `cancel_posthoc` (:315-325) mutates the registry without `_running_guard`.

28. **`ProcessingConfig.diarization` hardcoded `True` ("Default to true for
    testing")** — `processing_config.py:22`; computed value (:73) discarded.
    Every session pays per-utterance ECAPA + end-of-session clustering whether
    tagging was requested or not.

29. **autobahn `sendMessage` from worker threads** (audio):
    `processor_posthoc.py:232/:90`, `processor_speaker_metric.py:58-60`,
    `audio_stream_reader.py:30-32` — must go via `reactor.callFromThread`.
    Same class of bug in video: `videoprocessor.py:138-140, :286`,
    `facial_biometric_processing_service.py:92-94`.

### Video

30. **Decoder never recovers after a pipe break; one failing ffprobe per blob**
    — `server.py:166-176, 203-214` (8e6b12c): after a broken write it waits
    for a header that a webm stream only ever emits once per recorder start;
    meanwhile every 10s chunk spawns an ffprobe against a mid-stream cluster.
    Pod's live analytics silently dead for the session.

31. **Post-hoc enrollment starts a full embedding run per binary chunk** —
    `server_posthoc.py:347-351` (video service): concurrent ArcFace runs over
    the still-growing file race to write the same `.npy`; last (partial-clip)
    writer wins.

32. **Recorder write failures are `print`ed and dropped** —
    `video_processing/recorder.py:28-40`: on ENOSPC every chunk is lost while
    `bytes_received` keeps counting, so neither the no-video alarm nor the lag
    alarm fires — the exact silent-loss class those alarms were built to end.

33. **Blocking HTTP on the video reactor every 5s** — `server.py:769-770` →
    `is_valid_key()` → `requests.post(timeout=30)` per running connection
    (`connection_manager_impl.py:20-26`); plus `ProcessingConfig.from_json`'s
    two calls during `'start'` and `post_connect/post_disconnect`
    (`server.py:577, 582, 721`) — up to minutes of blocked ingest when the API
    server is slow.

### Frontend

34. **device-check `openPreview` race leaks camera/mic + AudioContext + rAF
    loop; can block the real join** — `device-check.jsx:180-316`: no
    generation token; `stopPreview()` can't clean a still-pending call; the
    orphan stream holds the camera (→ `NotReadableError` on session
    `getUserMedia` on many Androids). StrictMode double-mount hits it every
    dev load.

35. **"Session ended" is a dead-end blank page** —
    `byod-join-component.jsx:705` sets `ending.current` with no reachable
    reset; `join-machine.ts:86` is terminal; `html-pages.jsx` renders nothing
    for "ended" and the rejoin CTA prop (:2284) is passed but never read.
    Contradicts the comment at :702-704.

36. **Wake lock never released; `visibilitychange` re-acquirers stack forever**
    — `byod-join-component.jsx:333, 2133-2166` (per-render `let wakeLock`;
    one permanent listener per `handleStream`, ×5 on reconnect retries).
    Duplicated verbatim in `profile-creation-component.jsx:52, 623-656`.

37. **RecordingCoach rAF loops uncancellable** — `recording-coach.jsx:215,
    :237, :234, :303`: per-render `let meterRAF/visionRAF` means Stop/unmount
    cancels a stale id; the FaceDetector-per-frame loop burns CPU until tab
    reload. The recorder-tick loop already has the fix pattern (`rafRef`,
    :73-85) — apply it to the other two.

38. **pod-component inverted rxjs cleanup + stale interval id** —
    `pod-component.jsx:173-178` (`if (sub.closed) unsubscribe()` — should be
    `!sub.closed`) and :162-170 (clearInterval with the pre-commit state
    value): every pod visit leaks live subscriptions and a permanent interval;
    instructor tab lags progressively.

---

## P3 (selected; see per-area notes)

Server: set-literal `json_response` 500s in admin deletes (`admin.py:109, 162,
171`); broken `SessionDevice.__hash__` + `transcript.__hash__()` as id
(`tables/session_device.py:38-39`, `callback.py:217, 258`); dict assigned onto
a Text column (`llm_query.py:248`); topic-modeling global `stop_words` growth +
per-request spacy/LDA + cross-user uploads dir + shared `tempModel` TOCTOU
(`topicmodeling.py:23-100`, `routes/topic_model.py:16-71`); student merge moves
only `audiovideobiometrics/*.webm`, stranding the actually-used enrollment
artifacts (`admin.py:130-143`); `random` not `secrets` for reset passwords +
non-constant-time hash compares (`tables/user.py:64-68`); 15s busy-poll on the
request thread + unlocked `connections` (`device_websockets.py:44-59`);
data-quality admin report unbounded fan-out (`data_quality.py:123-145`);
`_remux_locks` unbounded (`session.py:275-276`); None-deref 500s instead of
404s (`database.py:519-522, 1219-1230`, `routes/device.py:31-32`);
`delete_session` failures logged at info (`session.py:128-136`,
`scheduled_tasks.py:40-41`); O(n×m) keyword filter in exports
(`session.py:1159-1163, 1261-1263`).

Audio: dead+broken `clusterEmbeddings` (`pyDiarization.py:214-260` — delete);
dead `speaker_metrics.process()` + uncalled `speaker_tagging/` package;
`add_stop_words` global growth + spacy per utterance + LIWC CSV re-parse per
utterance (`topic_modeling.py:47-74`, `features_detector.py:44`); AudioBuffer
float/int trim drift (~0.5s/hr) + unclamped negative extract offsets
(`audio_buffer.py:25-35`); live processor's broken `%d` log formatting (posthoc
already fixed — port it: `processor.py:311-321` vs `processor_posthoc.py:392-397`);
relative second-granular fallback embeddings filename + `results/*.txt`
accumulation (`processor.py:92-95, 288-290`); NME p-search O(n⁴) — cap
candidates before a 600+-utterance pod hits it (`pyDiarization.py:297-336`);
`_SharedWorker` readline without timeout deadlocks all pods while holding the
shared lock (`crisperwhisper_asr.py:107, 164`); Google live generator drops
collected chunks on the Empty race and skips `audio_time` on return paths
(`google_asr_connector.py:117-133`).

Video: duplicate `'start'` leaks ffmpeg + 3 threads (`server.py:518-582` — add
a `running` guard); `_kill_proc` zombie after kill without wait
(`server.py:216-229`); mp4 `video_count` never increments +
`video_files_accum` unbounded and unread (`server.py:319, 605, 623`);
pre-start heartbeat AttributeError log noise (`server.py:513-514`).

Frontend: `videoPlay` 3s backstop + 20s watchdog not cancelled on teardown
(`byod-join-component.jsx:542, 551-577`); cartoonify frame object-URLs never
revoked/trimmed (latent — feature disabled in UI; :1778-1783, :1980-2011);
`key={index}` on the mutable speaker roster (`html-pages.jsx:526` — use
`speaker.id`); posthoc-trigger run sockets + heartbeat survive unmount
(`posthoc-trigger.jsx:322-412`); `requestHelp` and RecordingCoach
`startPreview` swallow failures the user should see; profile-creation legacy
capture path is dead code with real bugs (delete it) and "Done" skips
`closeResources()` (:681); transcript/metric polling runs during the idle
speaker page — gate on `startDiscussionStreaming`
(`byod-join-component.jsx:625-640`).

---

## Verified clean (round 2)

- Throughput gauge (7760d13), lag math (761f5b1), no-video/lag watchdog timers
  (2cec6c9): no div-by-zero, timers cancelled, no races.
- Decoder feed path bounds (bounded queue, SENTINEL fits, drop-with-warning).
- byod socket/reconnect core, orientation-correct.js, all polling components'
  cleanup, video-player, polar-hr.
- `src/common/` (locking, timeouts, retry), `analytics.py`, `posthoc_queue.py`
  locking, `wrappers.py` session/device guards, `auth.py`.
- asr_connectors temp-file hygiene; all `requests` calls carry timeouts; no
  shell=True; no SQL string-building.

## Suggested fix order

1. One-liners with outsized payoff: #4 (frombuffer) + #22, #20 (argmax), #21
   (float embeddings), #23 (allow_pickle), #16 (folder guard), #38 (`!closed`).
2. Reactor-safety batch: #7 (sentinel try/finally + join timeout), #1 (app
   context + off-reactor DB), #33/#26 (HTTP + heavy work off reactor), #29
   (callFromThread).
3. Security/integrity: #2 (IDOR), #3 (rater overwrite), #11 (auth the
   synthesized endpoint), #14 (real unique constraint).
4. Lifecycle: #6 (restart analytics workers), #5 (Google STOP), #8 + #34-#37
   (frontend teardown batch), #27 (registry claim release).
5. The rest in listed order.
