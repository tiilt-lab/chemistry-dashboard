# Codebase antipattern & security sweep — running log

A rolling record of the antipattern/security sweep so it can continue across
sessions. Top section is what's left to do (start here); the bottom records
what's already shipped.

**Do the P0 items first — they are live, unauthenticated vulnerabilities.**

---

## P0 — Critical, live security holes (path traversal)

Found by audit 2026-08-07. The biometric-enrollment WebSocket handlers take an
`alias` (and `mimeextension`) straight off the socket JSON and interpolate it
into filesystem paths with **no validation and no auth** — the handlers run
before any Redis auth-key check, and the WS ports are proxied publicly
(`/audio_socket`, `/video_socket`). An `alias` like `../../foo` yields arbitrary
file **write, delete, and rename**; combined with the `allow_pickle=True` loads
below it is an RCE primitive.

The app's own alias charset is `a-zA-Z0-9._:' -` (max 64), defined at
`src/server/tables/speaker.py:18` (`NAME_CHARS`) and enforced by
`verify_characters` (`src/server/utility.py:44`). It excludes `/` and `\`, so
enforcing it at the socket boundary closes the traversal while still allowing
real names (e.g. "Evan Le"). The known-good reference is
`_face_thumb_path` at `src/server/routes/session.py:1029` (`os.path.basename`).

### Fix plan
1. Add `src/common/safe_names.py` with:
   - `safe_name(value)` → `os.path.basename(str(value).strip())`, then require
     it to match `^[A-Za-z0-9._:' -]{1,64}$` and reject `.`/`..`; raise on fail.
   - `safe_media_ext(value, default='webm')` → lowercase, strip leading dot,
     allowlist to `{webm, mp4, ogg, wav}`, else default.
   (`src/common` is already on the services' `sys.path` via the
   `connection_manager` import shim.)
2. Apply at each sink, rejecting the WS message (send an error) rather than
   crashing the handler.
3. Add a server-side helper too (`src/server/utility.py`) — `safe_name` for the
   Flask routes below — or reuse basename inline like `_face_thumb_path`.

### Sinks to fix (file:line — from the audit)
- **`src/audio_processing/server.py:126-134`** (`save-audio-video-fingerprinting`):
  `currAlias`/`mediaExt` → `video_file`; reaches `open(...,'ab')`
  (`recorder.py:50`), `os.remove` (`server.py:260`), wav write
  (`server.py:268`), and the `os.remove`/`os.replace` chain at
  `server.py:292,309,333,335,337,345`. Sanitize `currAlias` at 130 and re-check
  in `process_fingerprint_blob` (255-347). Allowlist `mediaExt` at 129.
- **`src/audio_processing/server.py:144-149`** (`add-saved-fingerprint`):
  `currAlias` → `wave.open(...+'.wav')`. Sanitize.
- **`src/video_processing/server_posthoc.py:185-196`** (same message on the
  video side): `currAlias` → `recorder.py:37` write / `recorder.py:46` delete,
  and `facial_biometric_processing_service.py:118,122` `np.save`. Sanitize
  `currAlias` at 189, allowlist `mediaExt` at 188.
- **`src/video_processing/server.py:164-169`** (`add-saved-fingerprint`):
  `currAlias` → `np.load(...+'.npy', allow_pickle=True)`. Sanitize **and** drop
  `allow_pickle=True` (or gate on a realpath-containment assert) — pickle load
  on an attacker-influenced path is RCE.
- **`src/video_processing/server_posthoc.py:268-270`**: `speaker["alias"]` →
  `np.load(..., allow_pickle=True)`. Same treatment.
- **`src/audio_processing/server_posthoc.py:190-191`**: `speaker["alias"]` →
  `wave.open(...+'.wav')`. Sanitize.

### Second-order (unauth write of a poisoned name → later file op)
- **`src/server/routes/student.py`** `/addstudent` (`:157`), `/updatestudent`
  (`:189`), `sync_student` ingress: **no `verify_login`, no charset check** on
  `username`. That username later builds paths at `_voice_paths` (`:22`), `:32`,
  `:83`, `:108` (`send_file` — arbitrary `.wav` read exfil). Add a
  `re.fullmatch(r'[A-Za-z0-9._-]{1,10}', username)` gate on write, and
  `os.path.basename` in `_voice_paths`/`:32`/`:83` to neutralize already-stored
  bad rows.
- **`src/server/routes/data_quality.py:74-76`**: `Speaker.alias` →
  `_enrollment_fields` / `os.path.join(_VOICE_DIR, alias+'.emb.npy')`. basename.
- **`src/server/routes/admin.py:127-135,146-149`**: student merge/delete does
  `os.remove`/`os.rename` on `{username}.webm`. Admin-triggered (so second
  order), extension fixed to `.webm`, but still unsanitized. basename; fixing
  the `/addstudent` input closes the source.

### Medium — untyped `sessiondeviceid` used as a glob prefix
- **`src/audio_processing/server_posthoc.py:341-342`** and message-parse sites
  `:114,203,244`; **`src/video_processing/server_posthoc.py:345`** parse-site
  `:202`. `data['sessiondeviceid']` is used raw as a `glob` prefix (never
  `int()`-cast, unlike `ProcessingConfig.from_json`). Currently *not* reachable
  as traversal only because of a `pathlib.Path.glob` implementation detail that
  changed in Python 3.13 — coerce to `int()` at the parse sites and add a
  `realpath().startswith(recordings_dir)` check. Same change fixes the audio
  glob's missing-separator bug (`"{id}*"` matches `9`→`91`,`918`; the video side
  already uses a trailing `-`).

---

## P1 — Hardening from the subprocess audit (2026-08-07)

Audit result: **zero shell=True, zero os.system, all 13 sites list-form** — no
injection vector. Only defense-in-depth items remain:

- **Sudoers scope** (`src/server/posthoc_queue.py:192`, `sudo -n systemctl
  restart blinc-audio-posthoc-processor.service`): confirm the NOPASSWD rule is
  pinned to *exactly* that unit, not `systemctl *` or `ALL`. Add `check=True`
  (or inspect `returncode`) so a sudoers misconfig logs instead of silently
  falling into the 240s port-poll timeout.
- **`int()`-coerce `sessiondeviceid`** — same as the P0 medium item above.
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
