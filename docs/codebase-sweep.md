# Codebase antipattern & security sweep — running log

A rolling record of the antipattern/security sweep so it can continue across
sessions. Top section is what's left to do (start here); the bottom records
what's already shipped.

**P0 (path traversal) is DONE — see the Done section. Start at P1.**

---

## P1 — Hardening from the subprocess audit (2026-08-07)

Audit result: **zero shell=True, zero os.system, all 13 sites list-form** — no
injection vector. Only defense-in-depth items remain:

- **Sudoers scope** (`src/server/posthoc_queue.py:192`, `sudo -n systemctl
  restart blinc-audio-posthoc-processor.service`): confirm the NOPASSWD rule is
  pinned to *exactly* that unit, not `systemctl *` or `ALL`. Add `check=True`
  (or inspect `returncode`) so a sudoers misconfig logs instead of silently
  falling into the 240s port-poll timeout.
- ~~`int()`-coerce `sessiondeviceid`~~ — done in `a1273f7`.
- **`asr_connectors/sortformer_diar.py:25`** uses deprecated, TOCTOU-racy
  `tempfile.mktemp()`; the sibling connectors use `NamedTemporaryFile`. Switch.
- **ASD `--candidates`** (`src/video_processing/server_posthoc.py:428`): aliases
  joined with commas; an alias containing a comma silently splits. Data-integrity
  only (charset excludes shell metachars). Consider repeated `--candidate` flags.

---

## P2 — Broader antipattern backlog (from the original sweep triage)

Not yet started. Roughly priority order:

1. **Resource leaks in the services.** `wave.open(...)` handles opened and never
   closed in fingerprint paths; moviepy `VideoFileClip`s not always closed. On
   long-lived processes these compound with the glibc arena fragmentation.
2. **Shared mutable state without locks.** `running_audio_processes`,
   `running_video_processes`, `image_queue_dict` are plain dicts mutated from
   worker, reactor, and request threads. Single ops are GIL-safe but
   check-then-set sequences (the "already running" guards) are racy.
3. **N+1 query patterns.** The export endpoints and `global_posthoc_queue` do a
   DB query per device per speaker per job in loops.
4. **Frontend lint enforcement.** ~90 unused-var hits, 236 `console.log`s, `==`
   vs `===`, `key={index}` on dynamic lists. Turn on `no-unused-vars`,
   `no-console`, `eqeqeq` as errors so they can't regress. Add `ruff`/`pyflakes`
   for Python.
5. **Deprecated / prod-risk infra.** `datetime.utcnow()` (deprecated), `!= None`
   throughout `database.py`, Werkzeug dev server in production (it warns every
   boot), flask-limiter in-memory storage (resets on restart, not shared across
   workers).
6. **Unbounded data growth.** `admin.py` reads the whole server log into memory
   then base64s it into a JSON response; stale `vid_img_frames_*` dirs and old
   recordings accumulate (disk hit 98%). Wants a retention policy.

Also open, tracked in `README.md`'s TODO section:
- Whether the anonymous student-dashboard/expert-rating surface needs a
  credential (currently reads transcripts/feedback with no auth by design).
- Pod processing keys now appear in nginx logs via the `?key=` media-URL param.

---

## Done (most recent first)

- **Security: path-traversal / name sanitization (P0)** (`a1273f7`) — new
  `src/common/safe_names.py` + `utility.safe_name`; every enrollment WS handler,
  post-hoc speaker loop, and server route that builds a path from an alias/
  username now sanitizes or rejects. `sessiondeviceid` coerced to int before
  glob use (also fixed the audio glob's missing `-` separator). Note for P1: the
  int-coercion covers the glob-prefix concern the subprocess audit raised, so
  that P1 bullet is effectively closed too.
- **Auth: HTTP callback timeouts** (`f45c845`) — every first-party callback POST
  now has a 30s timeout; a stalled Flask can no longer block a processing worker
  thread and pin the pod's in-RAM buffers.
- **Auth: unguarded device-scoped endpoints** (`89b9e7f`) — video/dynamics/
  heartrate/facethumb/gaze/joint_attention/posthoc/summary/speaker-CRUD now
  require `verify_device_read_access` (login *or* pod processing key, incl.
  `?key=` for media tags); localhost-only `verify_local` on the service
  callbacks and redis-key routes; BYOD client now sends its pod key on every
  call. Full route→caller audit done; anonymous student/expert routes left open
  by design and documented in place.
- **Frontend dedup + broken-Promise fixes** (`54d7bda`) — `response.json()`
  awaited everywhere; deleted ~1,200 lines of dead modules; shared TabBar /
  checklist / downloadBlob / getUserMedia helpers; several real bugs
  (crashing element ids, array-vs-number compares, frozen folder list).
- **Services dedup + copy-paste bugs** (`06c5411`) — shared `callbacks_common`
  and `audio_bytes` in `src/common`; fixed the dangling-else recorder crash,
  unguarded recorders, missing `return` in reduce_wav_channel, and the four
  "already running" guards that started a second concurrent run.
- **Server route bugs + dedup** (`034c442`) — export 500s, malformed join,
  unbound `success`/`output`, `_update_row` helper, ADMIN_ROLES, cartoonized
  stream fixes.
- **README TODOs for the two auth follow-ups** (`1cf7942`).
