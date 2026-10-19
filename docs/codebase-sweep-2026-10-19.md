# Codebase sweep — round 4 (2026-10-19)

Fresh discovery pass over `main` at 6bc6a21b: seven parallel reviews (server
data layer, server infrastructure + deploy, negotiation coding, audio +
`src/common`, video + dependencies + CI, frontend, cross-cutting redundancy +
tests). Nothing that `docs/codebase-sweep.md` (2026-08-09) marks fixed is
repeated; its deferred items that are still open are listed again. Every
finding was checked against the code at the cited line; the ones marked
*repro* were reproduced with crafted inputs; every P1 was re-read by the
coordinating reviewer.

Baseline at the start of the sweep: 990 Python tests pass locally in 34 s,
173 frontend tests pass, `tsc` passes, ruff reports zero violations, eslint
reports 37 warnings under the cap of 252.

Severity: **P1** = corrupts data, kills a feature, or security.
**P2** = wrong results, degradation, or stranded UI under real use.
**P3** = hygiene, latent, inefficiency, redundancy.
Tags: [bug] [inefficiency] [redundancy] [security] [privacy].

Changed in the working tree during this session (uncommitted): `README.md`
and `frontend/README.md` rewritten; `src/server/routes/session.py` no longer
refuses `POST /api/v1/sessions` under 10% free disk (logs a warning instead;
the disk was at 93% during a class). Later the same day all ten P1s below
were fixed (nginx `Host`, queue Stop scoping, negotiation attribution
persisted with the codes, timeline keys, timeline-recorder start recovery,
embeddings prepared once per run, late-add returns the slot and the audio
service stores a mid-session take, GET/DELETE query strings, CI installs the
skipped files' imports with a skip cap, the Google key deleted), plus the
join page's typed-username check (`voice_enrolled`), a saved-print failure
un-checking its card, an expedited enrollment from the join-page take
(`enrollment_check.enroll_take`), and a "Session concluded" dialog instead
of the navigation to an instructor page. Tests added beside each. The API
and the frontend build were reloaded; the live audio service needs a restart
to pick up its part.

---

## P1

### Deploy

1. **[bug] Both committed nginx configs send a duplicate `Host` header on
   `/socket.io`; gunicorn rejects the upgrade, so every dashboard page loads
   forever on a deploy from the repo** —
   `deploy/instances/blinc-puthipiroj/nginx-blinc.puthipiroj.com.conf:71-78`,
   `deploy/nginx.conf:63-70`. The location does `include proxy_params;`
   (Ubuntu's file already sets `Host $http_host`) and then
   `proxy_set_header Host $host;`; nginx emits both. Socket.IO is
   websocket-only (`app.py:81`), so there is no polling fallback. The host's
   live file was hand-fixed after the 2026-09-30 outage; the repo copies the
   README points installers at were not. Fix: delete the second
   `proxy_set_header Host` line in both files and add a contract test that
   greps the committed nginx files.

### Server

2. **[bug][security] The queue "Stop" button clears and cancels every
   session's post-hoc work, not the session's** —
   `src/server/routes/session.py:1425-1451`, `src/server/posthoc_queue.py:897-910`,
   caller `frontend/src/pods-overview/pods-overview-component.jsx:81`. The
   route is guarded by `verify_session_access(session_id)` but calls
   `posthoc_queue.clear_pending()` with no filter (every queued job of every
   session; `_coding_run_dropped` marks other users' coding runs cancelled),
   then loops over `posthoc_state.running_device_ids()` (every running pod on
   the host), sends `cancel_posthoc` to both services and `mark_done`s each
   whether or not the cancel landed. The route also hard-codes the post-hoc
   ports as 9015/9014 (see P2 #24). Fix: filter both passes to the session's
   device ids (`clear_pending(device_ids=...)`), `mark_done` only after a
   confirmed cancel reply.

### Negotiation coding

3. **[bug] What the paired merge decided about a line is never persisted, so
   the stored summary and every read-back disagree** (*repro*) —
   `src/server/negotiation_coding.py:1840` (`add_negotiation_codes`),
   `src/server/database.py:2317-2333` (stores only dimension keys plus
   `_text/_stitched/_speaker`), `negotiation_coding.py:1655-1680` (`code_row`
   rebuilds `speaker_tag`, `team`, `start_time` from the raw `Transcript` row
   and the *current* device sides), `database.py:2372-2377` (read-back
   ordered by raw `start_time`), `negotiation_coding.py:1862-1875`
   (`recompute_summary` re-rolls from `code_row`). `reconcile_clusters` may
   rename a cluster to the partner's student, `_unflag_unplaceable` may
   re-team a far-side row, and the clock alignment may shift one laptop's
   `start_time` by minutes; none of it is written. Reproduced on the test app
   stub: summary `by_team` {Pat 2, Sandy 2} vs read-back {Pat 3, Sandy 1}; a
   191 s offset reorders the read-back into all-Pat-then-all-Sandy and
   `PUT /teams` rewrites the stored summary to the wrong numbers. The panel's
   utterance list, the per-pod CSV and both session CSVs show pre-merge
   attribution while the roll-up on the same page counts post-merge. Fix:
   store `speaker_tag`, `team`, aligned `start_time` and merged `_text` on
   each `NegotiationCode`, prefer them in `code_row`, order by them, snapshot
   `sides` on the run.

4. **[bug] The de-escalation timeline cards have never shown a value** —
   `frontend/src/components/negotiation-coding/negotiation-coding-helpers.js:107-126`
   reads `first_escalating_s`, `peak_escalation_window_start_s`,
   `first_sustained_deescalation_s`, `first_future_move_s`;
   `src/server/negotiation_coding.py:1497-1501` sends the same keys without
   `_s`. Every card renders "—" / "Not observed." for every run since the
   panel's first commit. No test joins the two. Fix: drop the suffix in the
   helpers and add a test that imports the server's keys.

### Audio

5. **[bug] A service restart mid-session corrupts the pod's session-timeline
   recording, which the post-hoc run then prefers as its source** (*repro*) —
   `src/audio_processing/timeline_recorder.py:34-37, 48-68`,
   `src/audio_processing/server.py:538-539, 701-708`,
   `src/common/recording_fragments.py:277-285`. `TimelineRecorder.__init__`
   preloads `samples` from an existing `.dat` but leaves `start = None`; the
   first `write()` after a process restart sets `start` to the reconnect's
   session time while `end` is `start + old_samples/sr`, so the next frames
   are dropped as overlap and the track claims sample 0 is the reconnect
   time. `signal_end` writes a sidecar with that wrong `start_offset`, and
   `choose_recording` prefers `*_timeline_redu.wav` whenever it exists, so
   every row of the next post-hoc run is stamped minutes off and the first
   seconds after the reconnect are missing. Several such restarts happened
   on 2026-10-16. `tests/test_timeline_recorder.py:49-51` papers over it.
   Fix: read `start_offset` from the track's own `.clock.json` on
   construction (or persist `start` beside the `.dat`), refuse to append when
   unknown.

6. **[bug] Speaker-embedding bookkeeping races across the post-hoc worker
   pool; early embeddings are wiped and tagging fails** —
   `src/audio_processing/processor_posthoc.py:582-608` (same code live at
   `processor.py:352-380`). The `len(self.embeddings) == 0 and
   embeddings_file` check, the load and the `self.embeddings = []` reset run
   outside `_embeddings_lock`, and the first worker mints `embeddings_file`
   for a file that does not exist yet; with `POSTHOC_WORKERS = 4` the next
   workers log "Unable to load embeddings file" and assign a fresh list over
   the one another thread is appending to. Production evidence: one
   CrisperWhisper run on 2026-10-18 logged the error 487 times, posted 1031
   rows and ended "Processing results FAILED to post for tagging"
   (`handlers/callback_handlers.py:13-21` refuses a result set whose count
   differs). Fix: load a resume file once in `process()` before workers
   start; never reassign `self.embeddings` from a worker; mint the file
   name under the lock.

### Frontend

7. **[bug] "Add a participant" mid-session never opens the recorder; the
   late-arrival flow is dead on both join modes** —
   `frontend/src/byod-join/byod-join-component.jsx:1169-1182`
   (`addSpeakerSlot` has no `return speaker` on success), `:1516-1520`
   (`addLateParticipant` takes the `closeDialog()` branch), and
   `byod-join/html-pages.jsx:396-402` (the Options button on an audio join
   calls `openDialog("")`, so the dialog holding the action is unreachable
   for the default join mode, although `:620-625` promises it). Fix: return
   the speaker; open Options for audio joins too.

8. **[bug] `ApiService` drops the query object on GET/DELETE, so the admin
   "Clear Server Logs" for the audio service truncates the Flask server log,
   and every `/api/v1/devices` filter is ignored** —
   `frontend/src/services/api-service.js:111-113` (body only for non-GET/DELETE,
   no query-string path), `auth-service.js:335-352` (`log_type` passed as
   data), server `routes/admin.py:279-282, 321-326` (defaults to `dcs`);
   `device-service.js:7-19` (four filters, `routes/device.py:35-45` reads
   `request.args`). Selecting "Audio Processing Service" downloads the
   server log named `aps_logs.txt`; clearing it empties the wrong file.
   Fix: `URLSearchParams` for GET/DELETE in `_request`, plus a test.

### Tests / CI

9. **[bug] CI never collects 187 of the 990 tests, including all 114
   negotiation-coding tests** — `.github/workflows/ci.yml:20` installs only
   `pytest numpy scipy flask requests prometheus_client moviepy`; seven test
   files call `pytest.importorskip` at module level (`test_negotiation_coding.py`,
   `test_metrics.py`, `test_phase2_live_segment_split.py`,
   `test_api_phase1_ingest.py`, `test_posthoc_publish_batch.py`,
   `test_posthoc_reader.py`, `test_video_hwdec.py`; plus `test_enrollment_check.py`,
   `test_voice_prints_only.py`, `test_asr_vad.py`, `test_multiworker.py:398`
   gate on torch/soundfile/silero/socketio). The CI run for this commit
   reports `803 passed, 18 skipped`; locally `990 passed`. Fix: add
   `flask-sqlalchemy pyyaml soundfile python-socketio` to the pip line
   (pure Python), run the torch-gated files in a second job or fail the job
   when skips exceed a fixed small number.

### Secrets

10. **[security] A 2024 Google Cloud service-account key is still on disk at
    `src/audio_processing/asr_connectors/google-cloud-key.json`** (untracked,
    engine removed 2026-10-13; still referenced by the old README and
    `deploy/instances/blinc-puthipiroj/README.md:37`). Revoke it in GCP and
    delete the file.

---

## P2

### Server: data layer and routes

11. **[bug] `merge_students` moves speakers/video/LLM/survey rows but not
    transcripts, heart-rate or rater rows keyed by the same username** —
    `src/server/database.py:1382-1408` (five `.update()`s), consumers
    `database.py:1983` (`Transcript.speaker_tag`), `:1365-1371`
    (`student_teams`); `SpeakerHrMetrics.speaker_alias`, `Rater.speakertag`,
    `Rating.speakertag` also left behind. The surviving profile's
    longitudinal page loses every utterance of the merged sessions. Fix:
    four more `.update()`s in the same commit.

12. **[bug] Student merge/delete look for enrollment artifacts under
    `<root_dir>/chemistry-dashboard/...`, a path that does not exist** —
    `src/server/routes/admin.py:142-160, 176-188` vs `routes/student.py:19-21`
    (correct: `src/audio_processing/audiobiometrics`,
    `src/video_processing/facial_embeddings`). `os.path.isfile` is always
    False, nothing is logged, the route returns success: merges strand the
    survivor un-enrolled, deletes leave `.emb.npy`/`.check.json` behind, a
    deleted student still cross-matches new enrollments and can be attached
    by typing the old username [privacy]. Fix: share `_VOICE_DIR`/`_FACE_DIR`
    (ideally from `src/common`) and drop `root_dir`, which nothing else reads.

13. **[bug] `sanitize()` HTML-escapes names that are then validated or
    stored** (*repro*) — `src/server/utility.py:21-27`
    (`str(markupsafe.escape(v))`); `routes/session.py:332` (join group),
    `:1530` (rename pod), `:1302` (HR alias); `pod_config.py:27` allows `'`.
    "Pat's table" becomes `Pat&#39;s table`, which `verify_negotiation`
    rejects ("Invalid characters in group") and `rename_session_device`
    persists and shows escaped. JSON needs no HTML escaping: validate with
    `verify_fields`/`verify_characters` and store the raw string.

14. **[inefficiency] Every `/video` and `/video/info` request (each HTTP
    Range request of the player) runs ffprobe and three directory globs
    before the remux-cache check; `/video/info` repeats it** —
    `routes/session.py:490-523` (`_fixed_video_path`: probe at 503, cache
    check at 518), `:801-824`. Fix: cache-hit check first, encode the probe
    result in the cache name, pass `fixed`/`originals` into `_video_segments`.

15. **[bug] Anonymous LLM routes read and write any participant's stored
    feedback by guessable ids** — `routes/llm_query.py:175-229, 230-285,
    287-310`. Sequential ids, aliases visible on join pages, 3 concurrent
    slots the only cap. Open since the 2026-09-30 audit. Fix needs a
    per-student capability (token minted with `getstudentbyid`, or the pod
    key as `summary` at `:312-317` does), not a login gate.

16. **[inefficiency] `join_room` replays the whole session's transcripts and
    metrics to a pod page that wants one pod** — `routes/socket.py:63-100`;
    the client sends only `room` and last-seen ids. Several MB per pod-page
    open or reconnect on a 12-pod session. Fix: optional `session_device_id`
    in the join payload.

### Server: infrastructure and queue

17. **[bug] The post-hoc queue cannot see a run that fails before its first
    state poll and ignores the service's `error`/`end` messages; the lane
    stalls for the full 150-minute pod timeout** —
    `src/server/posthoc_queue.py:300-347` (`seen_running`, first poll ≥10 s
    after `start`), `:318-333` (`error`/`end` handled only for `rename`),
    `:49`; `src/audio_processing/server_posthoc.py:397-406, 738, 744-757`;
    `routes/callback.py:266-289` (`posthoc_failed` → `mark_done`). An ASR
    child dying at load (CUDA OOM, spawn failure) within that window leaves
    every job behind it waiting 2.5 h. The `posthoc_failed:<device>:<scope>`
    key written at `callback.py:286` is only read by metrics. Fix: treat that
    key (or the socket's `end`/`error` for every scope) as terminal, poll once
    right after `start`.

18. **[bug] `enqueue()` de-duplicates per pod regardless of legs; a
    record-only negotiation session ends with its coding run failing
    instantly and its audio leg never queued** — `posthoc_queue.py:851-864,
    561-568`, `handlers/session_handler.py:115-121` (video legs first, then
    coding), `negotiation_coding.py:1928-1933` (`enqueue(..., legs=("audio",))`
    return ignored). Sessions with `live_video_analytics=False` and
    `negotiation_coding=True`. Fix: dedup on `(device_id, leg)` or merge legs
    into the queued job; return skipped pods so `queue_coding_run` can gate.

19. **[bug] The queue recycles the audio post-hoc service on RSS alone with
    no idle check; a UI-triggered run in flight is killed** —
    `posthoc_queue.py:700-734` (only `_audio_service_rss() >= 14 GiB`),
    `frontend/src/components/posthoc/posthoc-trigger.jsx:504-507` (direct
    runs outside the queue). Fix: skip when `posthoc_state.running_detail`
    shows an audio/rename scope running.

20. **[bug][security] `RedisLogin.unlock_login` builds a SCAN glob from the
    account email; an account named `*` deletes every key in the Redis db
    when an admin unlocks it** — `src/server/redis_helper.py:26-27, 50-56`
    (keys `<email>-<ip>`, no namespace, `scan_iter(match=email+'*')`),
    `tables/user.py:31, 116-127` (`EMAIL_CHARS` admits `*`, `:`, `/`, no `@`
    required), `routes/auth.py:70-108` (open registration). Drops queue
    state, live presence, `APS-Auth-*`/`APS-Config-*`, tickets. Fix: prefix
    login keys, delete exact keys, require `@` in `User.verify_fields`.

21. **[bug] `SECRET_KEY` falls back to `os.urandom(32)` per process; under
    three gunicorn workers without `DC_SECRET_KEY` two thirds of requests
    reject the cookie** — `src/server/app.py:40-42`, `gunicorn.conf.py` (3
    workers). Production sets the key; a fresh install from the old README
    did not. Fix: refuse to start (or log an error) when `workers > 1` and
    the variable is unset. (The rewritten README documents it.)

22. **[bug] The committed nginx configs lack `client_max_body_size` and
    `proxy_read_timeout` for `/api`; on a fresh deploy video uploads over
    1 MB 413 and LLM/export calls over 60 s 504** —
    `nginx-blinc.puthipiroj.com.conf:81-84`, `deploy/nginx.conf:73-76`; app
    side `app.py:58` (6 GB), `llm_query.py:68` (600 s). The host file was
    fixed in Phase 0; the repo copies were not.

23. **[bug] Speaker write operations sit behind read-level guards; the
    socket connect trusts the cookie snapshot** — `routes/speaker.py:16-54,
    57-67` (a folder viewer can add, delete, rename speakers),
    `routes/socket.py:11-17, 45` (no DB re-read of the user, so a demoted or
    locked account keeps socket read for 7 days).

24. **[bug] Post-hoc port defaults disagree between the services and their
    clients** — services listen on `DC_AUDIO_POSTHOC_WS_PORT` default 9005
    and `DC_VIDEO_POSTHOC_WS_PORT` default 9004
    (`audio_processing/server_posthoc.py:915`, `video_processing/server_posthoc.py:644`);
    `posthoc_queue.py:47-48` and `routes/session.py:1443` default to 9015 and
    9014. Works on this host only because the units set the variables (and
    the coordinator unit does not set them at all, so it runs on the 9015/9014
    defaults that happen to match). A stock install's queue dials the wrong
    ports. Fix: one shared default per service in `src/common`.

25. **[security] The live audio and video websocket services bind every
    interface** — `src/audio_processing/server.py:755`,
    `src/video_processing/server.py:1157` (`listenTCP` without
    `interface='127.0.0.1'`); the device websocket, gunicorn and both
    post-hoc services bind loopback. Fix: bind 127.0.0.1; nginx is the only
    client.

### Negotiation coding

26. **[bug] A chunk whose indices do not match is silently coded as
    all-defaults; an off-by-one answer mis-maps every code to its
    neighbour** (*repro*) — `negotiation_coding.py:1328-1353`
    (`validate_codes`), `1365-1392` (`code_chunk` retries only on `[]`). A
    model that restarts numbering at 0 yields 40 `neutral/none/none` codes and
    a `done` run ("40 invalid codes dropped"). Fix: treat "fewer than N% of
    asked indices present" like an unparseable answer; reject index sets that
    are a shifted copy of the asked one.

27. **[bug] The "bleed" rule drops an unnamed laptop's own speech on time
    overlap alone, even with no shared words, inside a 5 s window after
    alignment** (*repro*) — `negotiation_coding.py:951-953, 936-944, 902`.
    On a laptop where nobody enrolled, every utterance starting within 5 s
    of a named line across the table is lost. Fix: minimum text similarity
    for `bleed`, or skip `side_unknown` rows.

28. **[bug] A scheme dimension whose key collides with utterance metadata
    corrupts or crashes the run; `normalize` reserves nothing** (*repro*) —
    `coding_schemes.py:136-230` (key = `slugify(label)`),
    `negotiation_coding.py:1411, 1466, 1655-1681`. A dimension labelled
    "Team" errors the run in `rollup`; "Text" replaces the utterance text.
    Fix: reserved keys in `normalize`; nest codes under `codes`.

29. **[bug] Deleting a scheme (or any divergence between a run's scheme and
    the session's current one) empties exports and badges; the delete dialog
    promises the opposite** (*repro*) — `negotiation_coding.py:1893, 1870`,
    `routes/negotiation_coding.py:128-137, 186-192`, `routes/coding_scheme.py:72-81`,
    `manage-coding-schemes-component.jsx:220-222`. Fix: snapshot the codebook
    on the run and read it back from there.

30. **[bug] Live-row sentence stitching hands a reply's first word ("No.",
    "OK.", "Mr.") to the previous speaker** (*repro*) —
    `negotiation_coding.py:1102-1110, 1145-1162`. Reaches the group
    transcript during class and any pod coded without a post-hoc pass. Fix:
    a sentence end at word 0 is not a tail.

31. **[bug] `tools/coding_eval/build_review_xlsx.py` rolls every utterance
    into "unassigned"** — `:227, :239` omit `names=VIKING_TEAMS`; broken
    since 2026-10-14; `tests/test_coding_eval.py` never imports it.

32. **[bug] The group-transcript cache fingerprint ignores the transcript
    text, so a manual edit shows the old words for up to 12 h** —
    `routes/negotiation_coding.py:347-358, 332`; edit route
    `routes/speaker.py:128-141`. Include `r.transcript`.

33. **[inefficiency] Coding is serial and single-threaded by default: 8-10
    min per group, about 2 h for a 12-group class, against a 25-min debrief
    window** — `posthoc_queue.py:119-125`, `negotiation_coding.py:108`
    (`DEFAULT_LLM_PARALLEL = 1`, four llama slots). Fix: concurrency = slots
    when no class is live.

### Audio

34. **[bug] Any utterance shorter than one ECAPA frame abandons a whole
    no-roster post-hoc run** — `processor_posthoc.py:599, 640-648`,
    `src/common/posthoc_staging.py:78-80`. `embedSignal` on a sub-25 ms clip
    raises (seen 4× post-hoc, 7× live); post-hoc `mark_failed()`s and
    `_abandon` keeps the old results after minutes of transcription. Fix:
    skip the embedding, keep the row (as live does).

35. **[bug] 46% of the LIWC dictionary never matches: wildcard entries are
    compared with `==`** (*repro*) —
    `features_detector/respeaker_hi_liwc.py:104-113`; consumers
    `features_detector.py:14-27, 43-55`. 4,894 of 10,565 entries are stems
    (`certain*`, `assur*`); "certainly" scores nothing. Every E&T value under
    the default `scorer=liwc` is systematically low on stemmed categories.
    Fix: exact-word sets plus `startswith` on a stem list.

36. **[bug] Topic modeling is wired to a directory and a spaCy model that do
    not exist; a session that selects a topic model gets a dead live pod and
    an abandoned post-hoc run** (*repro*) — `processor.py:86-91`,
    `processor_posthoc.py:158-163`, `src/common/topic_modeling_common.py:18-22`
    (`en_core_web_sm` absent from venv-unified), `topic_modeling.py:54-66`
    (per-utterance frequency filter leaves `doc2bow` empty), server writes
    models to a different cwd-relative `topicModels/`
    (`routes/topic_model.py:52-80`). Live: `AudioProcessor.start()` raises
    before `running = True` and the start reply. The UI still offers
    `topicModelId`. Fix: remove the feature or wire one absolute directory,
    install the model, guard the load.

### Video

37. **[bug] Video post-hoc analyses only the newest recording fragment of a
    pod; everything before a reconnect is silently skipped** —
    `src/video_processing/server_posthoc.py:481-508` (`files[-1]` by mtime);
    filenames per connection at `server.py:883`; the API side returns all
    segments (`routes/session.py:408-418`) and audio joins fragments. Then
    `post_posthoc_completed` stamps the pod analysed. Fix: iterate ordered
    segments (or the remuxed `videorecordings_fixed` copy) with per-segment
    `adjust_time`.

38. **[bug] Live video: any roster member without a saved face print aborts
    the `done` handler; every face is then labelled "Person N"** —
    `server.py:797-802` (`KeyError` on `self.facial_embeddings[speaker["id"]]`
    before `setParticpantFacialEmbeddings`), client sends
    `add-saved-fingerprint` only for typed enrolled usernames
    (`byod-join-component.jsx:1429-1438`) but `done` carries the whole
    roster. Latent (live analytics off in production). Fix: `.get()` and
    always set the embeddings.

39. **[bug] Post-hoc video: one failed detection batch fails the whole run,
    and the same failure inside the `finally` flush escapes without
    `on_run_complete`** — `attention_tracking/detect.py:460-471` (returns
    None), `video_cartoonizer/videoprocessor_posthoc.py:225-226, 269-272,
    280-283, 305-306`, `VideoMetricProcessor.py:148`. Lease and `_run_active`
    held until the socket closes; the queue waits out `_POD_TIMEOUT`. Fix:
    tolerate None in `worker()`, wrap the final flush.

40. **[bug] Both gaze models are fed BGR frames while they expect RGB** —
    frames are made BGR on purpose (`server.py:330` rgb24 →
    `videoprocessor.py:328` `COLOR_BGR2RGB`; `detect.py:763-767` documents
    it); `attention_tracking/utils/dataset.py:35, 49` passes them to
    DINOv2/ModelSpatial unswapped with RGB mean/std. Related:
    `facial_biometric_processing_service.py:21-34` hands dlib BGR and
    insightface RGB (`facial_recognition_backend.py:48-51, 79-81`);
    consistent between enrolment and matching, so recognition works, but
    off-distribution. Fix together; magnitude unmeasured.

41. **[bug] Live video metrics thread has no exception guard; one
    `return None` path kills it for the process lifetime** —
    `VideoMetricProcessor.py:112-126, 152, 214-216`. Fix: try/except in
    `worker_loop`, return `({}, [])`.

42. **[bug] Post-hoc video `Initialize` does the first-run model load, two
    HTTP round-trips and `nvidia-smi` on the reactor thread; the queue's 60 s
    init wait can time out and the job is marked failed, not deferred** —
    `server_posthoc.py:302-402`, `processing_config.py:114-116`,
    `src/common/gpu_lease.py:207-209`, `posthoc_queue.py:282, 779-781`
    (`asyncio.TimeoutError` is neither `_GpuBusy` nor `_LegTimeout`). Same
    class on the audio side (P3 #71). Fix: `defer_blocking` the load, ack
    from the callback; catch `TimeoutError` in `_init_phase`.

43. **[bug] `video_processing/config.ini.example` turns on cartoonify and
    live analytics whose weights are not shipped; a fresh install crashes the
    live video service at start-up** — `:35` `cartoonize = true`, `:38`
    `processvideoanalytics = true` (production: both false);
    `server.py:1125-1126` → `torch.load('checkpoint/...')` on a git-ignored
    directory; even with it off, `server.py:628` constructs
    `VideoCartoonifyLoader()` at import, which downloads a dlib model from
    the network when missing. Fix: example defaults false, lazy loader.
    (The rewritten README warns about it.)

### Cross-service

44. **[redundancy][bug] Two callback retry queues with drifted policy; audio
    disconnect never got the 10-minute window** —
    `src/audio_processing/callback_retry.py:1-160` vs
    `src/video_processing/callbacks.py:112-245` (same constants, implemented
    twice; audio retries 408/429, video treats every non-5xx as permanent);
    `src/audio_processing/callbacks.py:216` →
    `src/common/callbacks_common.py:64-82` (8 attempts, about 2 min), so an
    audio pod that disconnects during an API outage longer than 2 min stays
    "connected" on the dashboard. Mirrored test files too. Fix: `RetryQueue`
    in `src/common`, video uses it, audio disconnect goes through it.

45. **[redundancy][bug] Seven byte-identical post-hoc server helpers, and
    the one that differs is a drift** — audio `server_posthoc.py:101-104,
    163-177, 192-209, 243-264, 684-690` vs video `server_posthoc.py:92-112,
    131-146, 253-265, 512-520`. Audio `_release_gpu` gained
    `torch.cuda.empty_cache()` on 2026-10-19; video did not, so a video run
    keeps its allocator reserve until the 180 s recycle and an audio run
    queued right after waits for `DC_AUDIO_POSTHOC_MIN_FREE_MIB`. Fix: a
    `posthoc_server_common.py`; port `empty_cache`.

46. **[redundancy] Dead API surface still routed: keyword lists, topic
    models and uploads, data-quality report, speaker-transcript routes** —
    `routes/keyword.py:12-76` (6 routes), `routes/topic_model.py:18-95`
    (`POST /uploads/<user_id>` `joblib.dump`s user content and runs
    spaCy/gensim on the request thread), `routes/data_quality.py:126`,
    `routes/session.py:968, 1032, 1040, 1063, 855`, `routes/speaker.py:70-84`,
    `routes/admin.py:30-37`, the cartoonize pair `routes/session.py:1841-1901`
    (+ `_IMAGE_QUEUE_*`, `redis_sync.capped_push`). No frontend, test or tool
    caller (the pages became redirects on 2026-10-14; `create-session`
    declares `selectedKeywordList`/`selectedTopicModel` with no setter).
    `wrappers.verify_keyword_list_access/verify_topic_model_access` and
    `authz.resolve_device` die with them. Also importing the topic-model
    stack (pandas, gensim, PyPDF2, spacy) into every API worker.
    `POST /sessions/<sid>/devices` (`device_join_session`) has no UI caller
    but is API-client reachable: confirm before removing.

47. **[redundancy] Removed engines are still installed in the production
    venv and one test depends on them** — `src/venv-unified` (15 GB) still
    holds whisperx, faster-whisper, ctranslate2, pyannote-audio;
    `src/venv-unified-prev` is a second 15 GB copy;
    `src/requirements-unified.txt` still pins asteroid-filterbanks, julius,
    lightning, pytorch-lightning, pytorch-metric-learning,
    torch-audiomentations, torch_pitch_shift, torchmetrics, omegaconf
    (nothing imports them; the deptry lock check only verifies direct deps
    are pinned). `tests/test_asr_vad.py:74-92` takes its only real-speech
    fixture from `pyannote.audio/sample/sample.wav`, so after the rebuild the
    Silero gate's real-speech test silently skips. Fix: rebuild, prune the
    lock, vendor a short CC0 speech clip under `tests/`.

### Frontend

48. **[bug] Session metrics export silently truncates at the first `#` and
    mislabels JSON as CSV** — `pods-overview-component.jsx:436-446`
    (`encodeURI` leaves `#` unescaped in a `data:` URL). Use
    `utilities/download.js` `downloadBlob`.

49. **[bug] Login never shows the server's reason (locked, rate-limited,
    wrong password all read "Login failed")** — `auth-service.js:74-93` hands
    the raw `Response` to `setLoginStatus`; `login-component.jsx:31-36`
    reads `.message` off it. Fix: `await response.json()` on non-200.

50. **[bug] Expert-rating Reflection dashboard spins forever when the
    LLM/metrics load fails** — `expert-rating-component.jsx:349-357, 518-531`;
    the student dashboard already handles it. Mirror that.

51. **[bug] Pods overview polls `/triage` every 10 s for ended sessions,
    forever** — `pods-overview-component.jsx:67` tests `session.ended`, a
    field the model does not have (`models/session.js` has `end_date` and
    `recording`). Since 2026-07-20.

52. **[bug] Students page "Enrollment health" card always reports "no voice
    overlaps"** — `students-component.jsx:130-143, 174-181`
    (`voiceOverlaps.pairs` does not exist on the stored map).

53. **[bug] Create-session breadcrumb shows "Home" when opened from inside a
    folder** — `create-session-component.jsx:150-170, 197-213` (stale
    `folders` closure). Pass `folderresult` in.

54. **[bug] "View All" from the transcript dialog never jumps to the
    selected utterance** — `byod-join-component.jsx:2681`,
    `expert-rating-component.jsx:644` (`Object.keys(x) > 0` compares an
    array to a number). `student-dashboard-component.jsx:1021` has `.length`.

55. **[inefficiency] Pods overview re-renders and re-sorts everything every
    2 s from a `setInterval` copy of the store instead of subscribing** —
    `pods-overview-component.jsx:268-293`; the `BehaviorSubject`s already
    emit on change.

56. **[inefficiency] Sessions list refetches sessions and folders on every
    dialog open/close** — `sessions-component.jsx:54-90` (effect deps
    `[currentForm]`).

57. **[inefficiency] Pod page fetches the same `/dynamics` payload three
    times** — `session-vitals.jsx:17`, `speaker-cards-panel.jsx:62-63`,
    `conversation-dynamics-panel.jsx:338-339`.

58. **[inefficiency] PosthocTrigger and the reflection dashboard define
    sub-components inside render, so the whole form remounts every second
    during a run** — `posthoc-trigger.jsx:616-642, 131-137`,
    `reflection-interactive-dashboard.jsx:153-230`. Hoist to module scope.

59. **[inefficiency] Video analytics panel recomputes every bin and tally on
    each playback tick** — `video-analytics-panel.jsx:377-470` (no
    `useMemo`, ~2 updates/s).

60. **[inefficiency] Inline device check calls `setLevels` at 60 fps for as
    long as the join form is open** — `device-check.jsx:300-313`.

---

## P3 (selected; the per-area reports in the scratchpad hold the rest)

### Server

61. [bug] `session_device_transcripts` skips the pod-membership check its
    siblings apply — `routes/session.py:957-961` vs `:1063-1066`.
62. [bug] `help_button` accepts any pod's key for any pod id —
    `routes/session.py:1508-1520`, `wrappers.py:44-48`.
63. [bug] `pod_join_session` logs `pod.pod_id`, which does not exist; the
    LED `color` command is skipped on failure — `handlers/session_handler.py:256-258`.
64. [bug] Analysis-config PUT compares an escaped string to `-1`; clearing
    the topic model would 500 — `routes/session.py:188-191`,
    `database.py:697-712` (caller is dead).
65. [bug] The audio producer omits falsy fields, so topic 0 and bearing 0 are
    stored as -1 — `src/audio_processing/callbacks.py:82, 88`;
    `routes/callback.py:355-375`. Use `is not None`.
66. [bug] Session creation and ending straddle MySQL and Redis without
    compensation — `handlers/session_handler.py:15-84, 90-112`.
67. [bug] Idempotent ingest is check-then-insert with no unique key across
    three workers; `X-Idempotency-Key` is sent by both producers and read by
    nothing — `database.py:997-1050`, `routes/callback.py:383`.
68. [inefficiency] N+1 and per-row commits: `get_session_triage`
    (`database.py:1862-1884`, polled live), `update_transcript_features_batch`
    (`:1072-1089`), `set_speaker_tag` per row at session end,
    `create_byod_session_device` per slot (`:912-916`),
    `global_posthoc_queue` per job (`routes/session.py:1394`), `student_teams`
    (`:1365-1371`), `audio_posthoc_completed_at` (`:2207-2215`), windowed
    exports (`routes/session.py:1663, 1773`).
69. [inefficiency] `upload_video_session` still runs `f.save` + ffmpeg
    (600 s) on the request thread and bypasses the disk guard —
    `routes/session.py:1330-1362` (sweep #18 still open).
70. [bug] `enqueue_posthoc` 500s on a non-numeric device id —
    `routes/session.py:1415-1416`.
71. [inefficiency] Blocking work on the audio post-hoc reactor during init
    (sweep #26, still open) — `server_posthoc.py:629-671` (fragment
    convert/stitch up to 1800 s), `:317, 768-790`, `:353-362`, `:738`,
    `:696-698, 446-447`; the queue waits 60 s for the init ack.
72. [bug] Health endpoint omits the coordinator and the GPU exporter, and
    spawns 11 subprocesses per request on a 5 s poll —
    `routes/health.py:17-23, 34-44, 72-89`.
73. [bug] A stalled init ack surfaces as an empty error string —
    `posthoc_queue.py:282, 779-781`.
74. [bug] `_mutation()` proceeds without the cross-process lock after 20 s
    and holds a 10 s-TTL lock around DB work — `posthoc_queue.py:112,
    150-156, 206-213`.
75. [inefficiency] APScheduler starts in every gunicorn worker with no jobs
    (20-thread pool + unused processpool) — `app.py:104-120`.
76. [inefficiency] `/metrics` scrape has write side effects
    (`_prune_settled`) and duplicates Redis work — `routes/metrics.py:381-393`.
77. [bug] Pool arithmetic no longer matches the multi-worker layout: 3×50 +
    coordinator 50 = 200 connections vs MySQL `max_connections` 151 —
    `app.py:87-97`, `gunicorn.conf.py`.
78. [bug] Device-websocket DB work still runs on the Twisted reactor thread
    (sweep #1 deferred part) — `device_websockets.py:36-60, 143-199`.
79. [inefficiency] Double logging: root `FileHandler` + `StreamHandler`
    under gunicorn (four processes append to one file with copytruncate
    rotation, plus journald) — `app.py:29-34`.
80. [bug] CSP `report-uri /api/v1/csp-report` has no route; `img-src
    http://127.0.0.1` is meaningless; `X-XSS-Protection` obsolete —
    `deploy/nginx-headers.conf:4`.
81. [redundancy] Dead module globals and config: `app.py:68` (`r =
    redis.Redis`), `:84` (`DATABASE_FILE`), `config.py:13-16` (`cloud()`),
    CORS entries `"127.0.0.1:5000"`/`"localhost"` that can never match
    (`app.py:81`); `config.ini.example` lacks `proxy_count`.
82. [redundancy] Duplicate query helpers in `database.py`:
    `get_speaker_video_metrics_by_session_alias` (:274),
    `get_transcripts_by_session_alias` (:1125), `get_video_metrics_by_session`
    (:398), `get_all_transcript_metrics_by_session_by_timeline`.
83. [redundancy] Comments contradicting code: `posthoc_state.py:81`,
    `tables/session_device.py:82`, `database.py:656, 1780-1797`,
    `posthoc_queue.py:4-5, 683`, `routes/socket.py:26-28`,
    `routes/student.py:15-18`.

### Negotiation coding

84. [inefficiency] `_drop_covered` is O(rounds × n²): 200 rows 0.9 s, 400
    rows 5.5 s, 800 rows 36.6 s on synthetic covered rows —
    `negotiation_coding.py:1020-1067`.
85. [inefficiency] Every GET of the coding panel globs the recordings
    directory and re-resolves the scheme; the session overview endpoint
    multiplies that per pod and has no caller —
    `negotiation_coding.py:1878-1899, 747-760`,
    `routes/negotiation_coding.py:280-296`.
86. [bug] `_names_team`/`_alias_number` match on `team[:3]` —
    `negotiation_coding.py:477-484, 2027-2036`.
87. [bug] A duplicate's merged text (what the model coded) is not surfaced
    in the read-back — `:948, 1216, 1667`.
88. [bug] `_partner_on_own_clock` uses the 10-minute alignment samples and
    indexes the wrong clock in one direction — `:2151-2164`.
89. [privacy] Exports name students by username wherever `speaker_labels`
    has no roster side; the per-pod CSV always does —
    `routes/negotiation_coding.py:41, 135, 212, 260`.
90. [security] A session may point at any user's stored scheme by id —
    `routes/session.py:265-270` (no owner check).
91. [latent] Legacy Viking columns mirrored for any scheme reusing
    `emotion`/`rip`/`frame` with 16/16/32-char limits —
    `tables/negotiation_code.py:18-20, 37-41`, `coding_schemes.py:24`.
92. [latent] A run can be stranded `queued`/`running` with no timeout; the
    panel polls forever — `negotiation_coding.py:1902-1935`,
    `negotiation-coding-helpers.js:350`.
93. [redundancy] Dead: `DIMENSIONS` (`:119`), the `path != CODEBOOK_PATH`
    branch of `load_codebook` (`:138-146`), `TEAMS` alias (`:117`),
    `negotiation-coding-service.js exportCsv()`,
    `GET /api/v1/sessions/<id>/negotiation_coding`. Tests: dead `… if False
    else …` at `test_negotiation_coding.py:1533`; `create_session` source
    string-pinned three times; no paired-merge test reaches persistence;
    `tools/coding_eval/README.md:91, 169` stale.

### Audio

94. [bug] `recording_time` is not the inverse of `session_time` across a
    backward clock move (*repro*) — `src/common/recording_sidecar.py:80-97`;
    used by `moss_naming.session_prints` and `moss_rename.piece_turns`.
95. [bug] P&I / E&T recomputation on a pod without a recording claims the
    shared key `"No key"` and posts under it, so it silently no-ops —
    `server_posthoc.py:490-514`.
96. [bug] A post-hoc publish wipes-then-posts with a best-effort wipe —
    `processor_posthoc.py:241-276`, `callbacks_common.py:21-25, 85-90`.
97. [bug] Claims and the GPU lease leak when a client initialises and
    disconnects before `start` — `server_posthoc.py:430-455, 495-514,
    539-558, 792-827`.
98. [latent] Chunk-wise FFT resampling drift and out-of-band energy;
    `reformat_data` wraps floats outside ±1.0 instead of clipping (*repro*) —
    `src/common/audio_bytes.py:12-26` (dormant: the client fixes 16 kHz).
99. [latent] Multi-channel pods feed interleaved audio to the embedder and
    the wrong byte depth to DOA — `server.py:289-293`, `processor.py:290-292,
    311-321, 369-370`.
100. [bug] Re-sending the roster mid-session resets participation metrics
     and session-adapted prints — `server.py:119-132`,
     `speaker_metrics.py:67-89`, `pyDiarization.reset_speaker_session_state`.
101. [bug] `communication_density` is posted, stored and shown but never
     computed (always 0) — `speaker_metrics.py:89, 205`.
102. [bug] A failed re-enrollment take destroys the student's existing good
     voice print — `enrollment_check.py:276-283`, `server.py:447-451`.
103. [inefficiency] Per-frame `open()`s on the reactor (`recorder.py:17-23`,
     `timeline_recorder.py:54-68`); duplicate Redis GET per start
     (`processing_config.py:78-79`); keyword embeddings re-encoded per
     utterance (`keyword_detector.py:58-59`); three copies of the recording
     in the post-hoc reader (`audio_stream_reader.py:60-84`); O(n²)
     `calculateNewness` (`speaker_metrics.py:110-139`); post-hoc ECAPA on
     CPU while the run holds the GPU lease (`server_posthoc.py:63`).
104. [redundancy] Dead: `cluster_reconcile.py:20-28, 40-111`,
     `base_asr.py:181-198`, `float_to_timestamp` ×2, `recorder.py:58, 73-79`,
     `server.py:493-494`, `processing_config.py:36` (`config.tag`),
     `config.py` `root_dir`/`video_record_*`/`cartoonize_image_callback`/
     `topic_backend`, `callbacks_common.post_connect`, `respeaker_hi_liwc.py:8,
     81`, `liwc_composite.weighted_average`, `topic_modeling.py:22, 26`.
     Still duplicated live/post-hoc: `send_speaker_taggings`,
     `setSpeakerFingerprints`, nested `lemmatization`.
105. [redundancy] Config comments disagree on the keyword backend default
     (`config.py:101-105` word2vec vs `config.ini.example:28-32` embedding).
106. [policy] Callback retries give up after about 9 min; 13 metrics rows
     were dropped during an API outage on 2026-10-16 — `callback_retry.py:49-50`.

### Video

107. [bug] Live `start` still performs blocking HTTP on the reactor —
     `server.py:849` (sweep #33 partially open).
108. [bug] Record-only path depends on `[videorecord] original=true`; with it
     off every chunk raises; `reduced=true` writes the wrong file —
     `server.py:881-887, 908-912, 942, 949`.
109. [bug] Decoder silently stays off when the first blob is not a container
     header — `server.py:403-405, 417-421`.
110. [bug] Per-pod eviction keyed by `auth_key` races a same-key reconnect —
     `server.py:855, 873, 1076-1090`.
111. [bug] Post-hoc video run can wedge forever (ffmpeg with `check=True`, no
     timeout) and block the idle recycle; a recording without an audio
     stream fails the video run for a by-product nobody reads —
     `videoprocessor_posthoc.py:188-190, 200-211, 257-267`,
     `server_posthoc.py:140-141`.
112. [inefficiency] Post-hoc video extracts and concatenates a WAV nobody
     consumes, one ffmpeg per 10 s chunk (O(n²) seeks) —
     `videoprocessor_posthoc.py:172, 197-212, 250-267`. The 2026-09-30
     audit's "7.8 GB of WAVs" item.
113. [inefficiency] Post-hoc final partial batch is analysed twice —
     `videoprocessor_posthoc.py:245-248, 280-283`.
114. [inefficiency] Per-head `torch.cuda.synchronize()`, double fp16 casts,
     DataLoader collating 40 native frames, ResMasking forward without
     `no_grad`, allocator stats and full payloads logged per batch —
     `VideoMetricProcessor.py:150-162, 193, 219`, `detect.py:219, 234, 433,
     447-448, 598`, `emotion_detection_model.py:42-60`.
115. [inefficiency] Per-chunk and per-heartbeat INFO logging; dead
     heartbeat reply branch — `server.py:832-838, 943`.
116. [inefficiency] Key-validity sweep POSTs to the API every 5 s per pod
     (grace is 600 s) — `server.py:1141-1142`, `connection_manager_impl.py:21-55`.
117. [redundancy] Dead or duplicated video code: `redis_helper.py`,
     `global_singleton_lock.py` (no importer); `server.py:629` unused
     `EmotionDetectionModel()`; `detect.py:505-554, 810-867, 894-912` and the
     `sv.ByteTrack()` at `:206` (only use of `supervision`); `worker_posthoc`
     duplicates `worker`; `videoprocessor.py:81-118, 183-315` cartoonify
     body; `server.py:1026-1030`; `server_posthoc.py:57-58` module-level
     `VideoMetricAnalytics`; `config.py:40-50` accessors with no callers;
     `recorder.py:4-6` star-imports moviepy; `callbacks.py:96-151`
     idempotency header nothing reads.
118. [redundancy] Live video has its own Prometheus exporter with its own
     env var (`DC_VIDEO_METRICS_PORT`) beside `src/common/blinc_metrics`
     — `server.py:167-234`; no `blinc_process_*`/`blinc_service_up{video}`.

### Frontend

119. [bug] Discussion-graph contributions pie: every wedge starts at the
     same angle (state read inside a loop) — `discussion-graph-component.jsx:225-236,
     274-289`.
120. [bug] Pod/transcripts edits never reach the shared store; the next live
     event reverts them on screen — `pod-component.jsx:410-470`,
     `transcripts-component.jsx`.
121. [bug] `CategoricalDistributionChart` calls a hook-using component as a
     function inside `useMemo`; TDZ reference in the empty branch —
     `categorical-data-visualization.jsx:193-210, 338-349`.
122. [bug] `getSessionDeviceForClient` uses a leading-slash path →
     `host//api/...` (breaks under the Vite proxy) — `session-service.js:131`.
123. [bug] Session toolbar duration has no hours; dead "End Pod" path would
     crash — `session-toolbar-component.jsx:35-78`.
124. [bug] Timeline slider drag guard checks the ref object, not `.current`;
     document listeners leak on unmount mid-drag —
     `timeline-slider-component.jsx:20-26, 61-84`.
125. [bug] Unencoded user input in URL paths (passcode, alias, typed
     username) — `session-service.js:59, 67, 71, 272-285`, `auth-service.js:199`.
126. [bug] Small ones: Students "Edit name" opens the group/team dialog
     (`students-component.jsx:898`); byod `requestHelp` mutates state in
     place (`:2377-2392`); a successful join re-triggers the passcode lookup
     (`:2100`); video join with no supported MediaRecorder type sits on
     "Connecting…" (`:1783`); login 401 navigates to itself
     (`login-component.jsx:37-38`); live video metrics push raw JSON
     (`active-session-service.js:295-296`); expert-rating hard-coded study
     ids and null deref (`expert-rating-component.jsx:111-112, 285`).
127. [inefficiency] PosthocTrigger opens two probe websockets and an
     unconditional 15 s HTTP poll on every pod page; `/me` fetched twice
     per page load; `SessionManagerComponent` constructs a new
     `ActiveSessionService` every render; transcript panel recomputes per
     tick; `useD3` legend re-runs every render; toast timer resets —
     `posthoc-trigger.jsx:139-322`, `protected-route.jsx:27` +
     `app-shell.jsx:125`, `session-manager-component.jsx:9`,
     `transcript-panel.jsx:155-185`, `custom-hooks.js:7-12`,
     `pods-overview-component.jsx:188-192`.
128. [redundancy] Dead UI: the "Devices" step and device fetch in
     create-session (`create-session-component.jsx:126-148, 239-291,
     323-326`, `html-pages.jsx:510-585`); the "AddDevice" dialog in pods
     overview (`pods-overview-component.jsx:345-367`, `html-pages.jsx:860-900`
     would throw); the legacy capture path in profile-creation (sweep
     deferred item, still present; real consequence: the live enrollment
     flow holds no wake lock and never closes `audiows`/`videows` on
     unmount — `profile-creation-component.jsx:140-200, 350-452, 702`);
     the student-dashboard / expert-rating transcript drill-down with a
     latent crash (`transcripts-component_client.jsx:27-28`);
     `discussion-summary-panel.jsx` (unimported); unused service methods
     (`getPodHeartRate`, `updateSessionAnalysisConfig`, `getStudentProfiles`,
     `addDevice`), `custom-hooks.js:14-52`, `globals.js` trig helpers.
129. [redundancy] Three hand-rolled fetch paths beside `ApiService._request`
     — `session-service.js:12-25`, `sessions/html-pages.jsx:133-137`,
     `video-player.jsx:111-114` / `audio-player.jsx:30-33`.
130. [redundancy] npm: `react-select`, `underscore` unimported; `web-vitals`
     a no-op; `@types/react` 19 against React 18; `@tailwindcss/vite` and
     `tailwindcss` belong in devDependencies; two chart stacks; CRA
     leftovers (`eslintConfig`, `browserslist`, `components.json` →
     missing `src/App.css`, 0-byte `tailwind.config.js`, `manifest.json`);
     unused CSS tokens. Local `node_modules` has vitest 3 vs lock 5.
131. [redundancy] `key={index}` on mutable lists — `transcripts/html-pages.jsx:140`,
     `session-toolbar/html-pages.jsx:78, 101, 117`, `folder-select/html-pages.jsx:96`,
     `discussion-graph/html-pages.jsx` (×6); 22 `exhaustive-deps` violations
     under `lint:strict` (list in the frontend report).
132. [redundancy] Duplicated UI logic: reassign/edit/merge in pod and
     transcripts components; ~250 lines of synthesized-metrics / LLM cache
     machinery in both student-dashboard and expert-rating;
     `fmtElapsed`/`fmtEta` vs `queue-summary.js`; two `"… UTC"` date parsers
     beside `globals.stringToDate`.

### Cross-cutting, tests, hygiene, docs

133. [redundancy] `src/common/enrollment_token.py` and `posthoc_ticket.py`
     are the same module (prefix and TTL differ); mirrored tests with an
     identical `_FakeRedis`.
134. [redundancy] Six private fake-Redis classes beside `tests/fake_redis.py`
     (`test_enrollment_token`, `test_posthoc_ticket`, `test_distributed_claim`,
     `test_phase2_live_presence`, `test_phase2_posthoc_gpu_lease`,
     `test_pod_registry`). Absence pins that can no longer fail: seven
     `"google" not in …` asserts in `test_asr_factory.py:52-87`,
     `test_model_hygiene.py:19-27`, `test_phase2_posthoc_contracts.py:273`.
135. [redundancy] Dead Python modules: `src/video_processing/global_singleton_lock.py`,
     `src/server/consolidate_sessions.py` (CLI referenced nowhere),
     `video_cartoonizer/util.py` StyleGAN helpers, `emotions_dlib.py:687`,
     `emotion_detector/utils/utils.py:21`. Unreferenced manual scripts:
     `tests/manual/*.py`, `tools/best_channel.py` (decide, document or drop).
136. [redundancy] Tracked help export served by nothing: `src/UA/enu/` (207
     files, about 15 MB of PNGs, 26 of the repo's 30 largest blobs); only
     the legacy `deploy/nginx.conf:78-85` references it.
137. [redundancy] Orphan submodule: `.gitmodules` +
     `src/audio_processing/speaker_diarization/speechbrain` gitlink (empty
     directory; the code imports the pip package). `git rm --cached` it.
138. [inefficiency] 92 MB of model weights in git
     (`attention_tracking/yolo11m.pt`, `scuthead_yolov8m_head.pt`), in use;
     README says models self-download. LFS or download-on-first-use.
139. [bug] Rotated service logs land in the source tree and are not
     ignored (`*.log` but no `*.log.*`): 41 files, 32 MB. Writers:
     `app.py:29`, `audio_processing/server.py:729`, `server_posthoc.py:895`,
     `video_processing/server.py:1117`, `server_posthoc.py:617`,
     `crisperwhisper_asr.py:60`; `/etc/logrotate.d/blinc` rotates in place.
     Either ignore `*.log.*` or log to `/var/log/blinc`.
140. [hygiene] Repo-tree litter: 125 root-level `YYYYMMDD-HHMMSS.npy` files
     (20 MB, July 2026, output of a bug fixed on 2026-08-09; nothing reads
     them; safe to delete); `frontend/build.prev-*` ×5 (hand-made build-swap
     backups, no ignore rule); `tools/bakeoff/` (untracked, byte-identical
     copies of `triton_decode.py` and `flash_turing_attn.py` plus retired
     engine drivers); research artifacts (`docs/*.xlsx` with participant
     transcripts, `docs/*.docx`, root PDFs, `docs/pni-audit.*`,
     `server-load-report-2026-08-06.md`) — ignore `docs/*.xlsx docs/*.docx
     *.pdf` so they can never be committed. `src/audio_processing/audiobiometrics/`
     (227 `.check.json`) and `src/audio_processing/videorecordings/` (163 MB)
     are data directories inside the source tree with half-applied ignore
     rules; about 40 `.gitignore` patterns predate the `src/` layout and are
     inert; `*.npy` appears twice; `.gitignore` lists itself.
     `src/audio_processing/embeddings/` is never pruned; `recordings/` is
     41 GB with no retention policy (the disk hit 93% today).
141. [redundancy] Stale CI comments and caps: `ci.yml:35-39` says the ruff
     backlog cannot be zero while `CAP=0`; `:73-79` caps eslint warnings at
     252 against 37 today (215 new warnings would pass). `tools/ci/deptry_check.sh:28-31`
     still merges the deleted `requirements-unified-nodeps.txt`;
     `pyproject.toml:14` excludes the gone `src/venv-nemo` and not
     `src/venv-granite`/`src/venv-unified-prev`; `opencv-python` and
     `opencv-python-headless` both listed for one `cv2`;
     `src/requirements-direct.txt` keeps `google-api-core`,
     `googleapis-common-protos`, `protobuf` (Google Speech leftovers).
142. [bug] `tools/loadgen/loadgen.py` cannot run from the documented venv
     (`import websocket` not installed); `--out` defaults relative to CWD;
     `_poll_loop` keeps polling after `self.ended`.
143. [inefficiency] `deploy/monitoring/gpu_exporter.py` re-initialises NVML
     per callback, enumerates processes twice per scrape, unbounded `pid`
     label series and a name cache that never evicts.
144. [bug] `deploy/respeaker.rules:1` makes every CDC-ACM device
     world-writable (`KERNEL=="ttyACM*", MODE="0666"`); scope by vendor id.
145. [redundancy] Deploy templates drift from the live units (`TZ=UTC`,
     `OMP_NUM_THREADS=2`, `MALLOC_ARENA_MAX=2`, `DC_ASR_WORKERS=2`,
     `DC_ASR_VAD=silero`, secrets file on the live audio unit); every unit
     copies `LimitRTPRIO`/`LimitRTTIME` nothing uses; `deploy/nginx.conf` is
     the retired `videodev.tiilt-blinc.com` block; the instance directory
     and README still name the retired `blinc.puthipiroj.com`
     (`tests/test_multiworker.py:369-387` reads `deploy/instances/*/`, so
     rename rather than delete); the live host's nginx files are not in the
     repo.
146. [redundancy] Docs contradicting code (beyond the two READMEs rewritten
     today): `docs/model-profiles.md` (whisperx/pyannote post-hoc defaults,
     `diarization_fallback` and `[whisper] model_size` knobs nothing reads,
     `topic_backend=bertopic` unwired, emotion fallback `hsemotion` vs code
     `resmasking`, "the frontend posts posthoc_completed");
     `src/requirements-unified.README.md:34` (google-cloud-speech);
     `deploy/instances/blinc-puthipiroj/README.md` (Google key, `venv/bin`,
     three units); `docs/infra-audit-2026-09-30.md:52` cites an untracked
     report; stale engine comments in `segment_split.py:48`,
     `base_asr.py:103, 182`, `moss_run.py:2`, `audio_processing/callbacks.py:136`.

### Coverage holes (no test imports the module)

`routes/auth.py` (255: register, login, reset), `wrappers.py` (300: every
access decorator, where the 2026-08 IDOR fixes live), `routes/admin.py`
(341), `routes/llm_query.py` (377), `routes/data_quality.py` (155),
`utility.py` (1120: only `disk_free_fraction`; the ~800-line window-metric
chain is live and untested), `database.py` (2381: reached only through app
fixtures), `features_detector/*` (the E&T scoring on every row; the LIWC
bug above would have been caught), `keyword_detector.py`, `prosody.py`,
`vocal_emotion.py`, `pyDiarization.py` clustering, `emotion_detector/*`,
`facial_recognition_backend.py`, `videoprocessor.py`,
`VideoMetricProcessor.py`, `blinc_metrics.py` (1). Plus everything P1 #9
drops from CI.

---

## Verified clean (this round)

- Migration chain: one root, one head, every `down_revision` resolves; every
  column, index and constraint in `tables/*.py` exists in the chain; the
  previously deferred analytics indexes are in place; downgrades coherent.
- Producer/consumer payloads for every callback route match on both sides;
  every frontend service call targets an existing route with the right
  method and shape, except the GET-body cases in P1 #8.
- Authz on the session/device routes (`_device_in_session`,
  `verify_device_read_access`, folder levels, owner-scoped guards), token and
  password handling (pbkdf2, `compare_digest`, `secrets`, SHA-256 tokens,
  enumeration-safe reset), rate limiting, cookie flags, `ProxyFix` count.
- Multi-worker state: everything that must be shared is in Redis; the
  coordinator owns the single-instance services; Socket.IO websocket-only
  over the Redis queue; prometheus multiprocess bookkeeping.
- Post-hoc queue core (claims, leases, pre-emption, `_ServiceUnavailable`,
  adoption of runs finished while away), `posthoc_state`,
  `distributed_claim`, `pod_registry`, `posthoc_ticket`, `enrollment_token`,
  `live_presence`, `gpu_lease` heartbeat and release paths.
- Audio: `clock_anchor` sign/units, `asr_ingest` windows and VAD gate,
  CrisperWhisper pool/reaper/breaker, callback dedup, `completion_latch`,
  `segment_pool`, `posthoc_staging`, `audio_align`, `channel_select`,
  `recording_fragments` selection, MOSS naming/rename rules, AudioBuffer
  math, segment splitting, no raw `sendMessage` off the reactor.
- Video: sweep #6/#7/#30-#33 fixes hold (except the `start` HTTP in #107);
  decoder feed bounds, sentinel/joins, pipe-break recovery, callback retry
  queue, tickets enforced, lease released on every init failure path.
- Negotiation coding: audio-gate race, parsing/coercion, clock-alignment
  sign, anchor voting, `reconcile_clusters` direction, pair resolution,
  route authorisation, single-commit code replacement, PR #289 queue display.
- Frontend: byod teardown/reconnect/backlog/wake-lock/visibility paths,
  `startPolling`, `ActiveSessionService` generation tokens, auth routing,
  dialog primitives, players, services↔routes trace, no `innerHTML`/`eval`,
  lazy chunks; all 29 test files make real assertions.
- Monitoring: all 42 metric names in the Grafana dashboard and alert rules
  are emitted; scrape ports match `DEFAULT_PORTS` and the units.
- `redis_helper.py`/`connection_manager.py` in audio and video are 11-line
  shims onto `src/common`; `recorder.py` audio vs video are different
  classes, not drift.

## Branches

Deleted this session: local `master`, `remove-qwen3-research`,
`remove-whisperx`, `cleanup/readme-consolidation` and remote
`origin/cleanup/readme-consolidation` (PR #117 merged 2026-04-09). `main`
was history-rewritten, so the 22 remaining remote branches (other
contributors, 2023-10 to 2026-08, four of them with merged PRs) share no
merge base with it and cannot be merged; they are listed in the session
summary for a decision.
