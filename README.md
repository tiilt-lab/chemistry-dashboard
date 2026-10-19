# BLINC Discussion Capture

BLINC captures small-group discussions and turns them into live and post-hoc
analytics. Each group ("pod") records audio — and optionally video and Polar
heart-rate straps — from a browser or a hardware mic-array pod. The pipeline
identifies who is speaking from voice fingerprints, transcribes the speech,
and computes discussion metrics (participation, cohesion, keywords, questions,
emotions, gaze/joint attention) that facilitators watch on a dashboard while
the discussion is happening and dig into afterwards.

## How a session actually flows

1. **Sign in and create a session.** A facilitator logs into the dashboard,
   creates a session, and gets a word passcode (and QR code) to hand out.
   The session overview lists the session's pods as they join.

2. **Pods join.** A pod is one recording device covering one group:
   - **BYOD** — any laptop/tablet opens the join page and enters the passcode.
     Groups are auto-named `Group A`, `Group B`, … (a typed name overrides).
   - **Hardware pods** — ReSpeaker mic-array devices (see
     `deploy/respeaker.rules`) connect over the device WebSocket.

3. **Speakers enroll on the join screen.** Every speaker needs a voice
   fingerprint so the pipeline can attribute speech. Each speaker card offers
   a quick record (≥10 s of natural speech), or typing an *enrolled* username
   attaches that student's saved fingerprint. Full enrollment (longer voice
   sample with a quality gate, plus face capture for video) happens ahead of
   time in the profile-creation flow; embeddings are stored under the
   configured `root_dir` (e.g. `audiobiometrics/*.npy`). Polar H10 straps are
   paired per speaker via Web Bluetooth on the same screen.

4. **Live capture and processing.** On "start", the client streams:
   - **Audio** over `/audio_socket` to the audio processor: voice-activity
     segmentation → speaker ID (ECAPA embeddings matched against the pod's
     fingerprints) → ASR (CrisperWhisper 2.0, fully on this machine; the
     Google Cloud Speech option was removed) → per-utterance features: keyword matching
     (sentence embeddings), question detection, expression/thinking-style
     scoring (LIWC / open / LLM), participation and cohesion metrics.
   - **Video** (optional) over `/video_socket` to the video processor: face
     recognition against enrolled faces, facial emotion, gaze/attention
     (Gaze-LLE), object-of-focus (YOLO), joint attention.
   - **Heart rate** from paired Polar straps, sent via the REST API.

   The processors don't write the database themselves — they POST results to
   the Flask server's `/api/v1/callback/*` routes, which persist to MySQL and
   push live updates to dashboards over Socket.IO (Redis is the message queue
   and also carries session auth/config keys between server and processors).

5. **Watch live.** The dashboard shows per-pod transcripts and metrics as
   they arrive, with session-level rollups across pods.

6. **Post-hoc analysis.** After a session ends, heavier reprocessing can be
   triggered from the UI: MOSS end to end (transcript and speakers in one
   pass, named from the enrolled voice prints) or CrisperWhisper verbatim
   mode with voice-print matching, and a deeper video pass (head tracking with identity
   persistence, gaze overlays, configurable fps). Post-hoc runs are handled
   by two dedicated services; state and queueing live in
   `src/server/posthoc_state.py` / `posthoc_queue.py`.

7. **Review and correct.** Transcript text can be edited (the original ASR
   text is preserved), utterances can be reassigned to the right speaker
   (optionally relabeling a whole diarization cluster at once), and session
   video plays back with gaze overlays.

## Architecture

Five Python services (all run from one virtualenv, `src/venv-unified`), plus
nginx, MySQL, and Redis:

| systemd unit                    | Entry point                              | Port env var (code default)                         |
| ------------------------------- | ---------------------------------------- | --------------------------------------------------- |
| `blinc-discussion-capture`      | `src/server/discussion_capture.py`       | `DC_PORT` (5000, Flask), `DC_DEVICE_WS_PORT` (9001) |
| `blinc-audio-processor`         | `src/audio_processing/server.py`         | `DC_AUDIO_WS_PORT` (9000)                           |
| `blinc-video-processor`         | `src/video_processing/server.py`         | `DC_VIDEO_WS_PORT` (9003)                           |
| `blinc-audio-posthoc-processor` | `src/audio_processing/server_posthoc.py` | `DC_AUDIO_POSTHOC_WS_PORT` (9005)                   |
| `blinc-video-posthoc-processor` | `src/video_processing/server_posthoc.py` | `DC_VIDEO_POSTHOC_WS_PORT` (9004)                   |

nginx serves the built frontend (`frontend/build/`) and proxies everything
else, so the browser only ever talks to one origin:

| nginx location          | Backend                    |
| ----------------------- | -------------------------- |
| `/` `/assets/`          | `frontend/build/` (static) |
| `/api`, `/socket.io`    | Flask server               |
| `/device_socket`        | device WS (Flask side)     |
| `/audio_socket`         | audio processor            |
| `/video_socket`         | video processor            |
| `/audio_posthoc_socket` | audio post-hoc processor   |
| `/video_posthoc_socket` | video post-hoc processor   |

Multiple instances share one host by giving each its own `DC_*` ports,
MySQL database, Redis db number, and `root_dir` — see
[`deploy/instances/blinc-puthipiroj/README.md`](deploy/instances/blinc-puthipiroj/README.md)
for a worked example (that instance runs 5001/9010/9011/9013/9014/9015).

Repository layout:

```
frontend/            React + Vite app (dashboard, BYOD join, profile creation)
src/server/          Flask API, Socket.IO, MySQL models & migrations, post-hoc queue
src/audio_processing/  live + post-hoc audio pipeline, ASR connectors, speaker ID
src/video_processing/  live + post-hoc video pipeline (faces, emotion, gaze, heads)
deploy/              nginx configs, udev rules, per-instance systemd units
```

## Installing on a new machine

Target: Ubuntu 22.04+ with an NVIDIA GPU (the video pipeline and local ASR
need CUDA; CrisperWhisper is the only ASR, so a GPU is required for audio too).

### 1. System packages

```bash
sudo apt-get update
sudo apt-get install -y build-essential git curl pkg-config ffmpeg libsndfile1 \
    nginx mysql-server redis-server
sudo systemctl enable --now mysql redis-server
```

GPU: install the recommended NVIDIA driver (`sudo ubuntu-drivers install`)
plus CUDA 12.8 and cuDNN from NVIDIA's apt repos. The pinned torch wheels are
cu128 builds — a driver from the 570 series works; CUDA 13-only setups don't.

Python 3.13 is required for the unified venv (via miniforge/conda, deadsnakes,
or a system python3.13). Node 24 (the version CI builds with) for the
frontend (via [nvm](https://github.com/nvm-sh/nvm): `nvm install 24`).

### 2. Clone and create the Python environment

```bash
git clone https://github.com/tiilt-lab/chemistry-dashboard.git
cd chemistry-dashboard
python3.13 -m venv src/venv-unified
src/venv-unified/bin/pip install -r src/requirements-unified.txt --extra-index-url https://download.pytorch.org/whl/cu128
src/venv-unified/bin/pip install --no-deps -r src/requirements-unified-nodeps.txt   # whisperx: its metadata lags the stack
src/venv-unified/bin/pip install git+https://github.com/fkryan/gazelle
src/venv-unified/bin/python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

See [`src/requirements-unified.README.md`](src/requirements-unified.README.md)
for the hard pins and why (torch cu128 index, transformers, numpy 2).

### 3. Database

The MySQL password convention is *password = username*:

```sql
CREATE DATABASE discussion_capture;
CREATE USER 'blinc'@'localhost' IDENTIFIED BY 'blinc';
GRANT ALL PRIVILEGES ON discussion_capture.* TO 'blinc'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Configuration

Each component has a git-ignored `config.ini` created from its example:

```bash
cp src/server/config.ini.example           src/server/config.ini
cp src/audio_processing/config.ini.example src/audio_processing/config.ini
cp src/video_processing/config.ini.example src/video_processing/config.ini
```

Then edit:
- **`src/server/config.ini`** — `domain` (your hostname), `database_user` /
  `database_name`, `redis_db`, and `root_dir` (runtime file storage, e.g.
  `/home/<you>/blinc-data` — create it and make it writable by the service
  user). Optional `[sync]` section mirrors student profiles with a peer
  instance.
- **`src/audio_processing/config.ini`** and
  **`src/video_processing/config.ini`** — point the `[output]` callback URLs
  at your Flask port, set `redis_db` to **match the server's** (the server
  writes session auth keys the processors read), and set the same `root_dir`.
  This is also where you pick backends: `asr=crisperwhisper` (the only
  value; legacy keys map to it), `scorer=liwc|open|llm`, gaze/emotion/head
  models, post-hoc fps, etc.

### 5. Credentials

- **Google Cloud ASR** (default `asr` backend): put a service-account key at
  `src/audio_processing/asr_connectors/google-cloud-key.json`. For a fully
  open, offline pipeline instead set `asr=whisper` and `scorer=open`.
- **`/etc/blinc/secrets.env`** (optional; loaded by the systemd units): API
  tokens the pipelines read from the environment — `HUGGING_FACE_HUB_TOKEN`
  (gated pyannote diarization models), `GOOGLE_API_KEY` (only for
  `scorer=llm`), `GOOGLE_APPLICATION_CREDENTIALS` (to override the key path).
- The default `liwc` scorer needs the proprietary LIWC2007 dictionary; use
  `scorer=open` if you don't have a license.

### 6. Model assets

Most models (ECAPA speaker ID, sentence embedders, MOSS, CrisperWhisper, YOLO11,
hsemotion, Gaze-LLE/DINOv2) download themselves from Hugging Face / torch.hub
on first use. Two things need manual setup:

- **Head detector weights** in
  `src/video_processing/attention_tracking/pretrained-models/` — the vendored
  CrowdHuman `crowdhuman_yolov5m.pt` (default `head_model=yolov5`). The
  legacy checkpoints (`model_gazefollow.pt`, `yolov4-p7.pt`, ResMasking
  emotion checkpoint, GoogleNews word2vec vectors) are only needed if you
  switch the corresponding `config.ini` backends away from their defaults.
- **Database schema**:
  ```bash
  cd src/server && ../venv-unified/bin/flask --app discussion_capture db upgrade
  ```

### 7. Frontend

```bash
cd frontend && npm install && npm run build
```

nginx serves `frontend/build/` directly — rebuilding is deploying.

### 8. Services, nginx, TLS

Use the unit files in `deploy/instances/blinc-puthipiroj/` as templates:
edit `User`, `WorkingDirectory`, `ExecStart` paths, and the `DC_*` port
overrides for your machine, then:

```bash
sudo cp blinc-*.service /lib/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now blinc-discussion-capture blinc-audio-processor \
    blinc-video-processor blinc-audio-posthoc-processor blinc-video-posthoc-processor
```

Adapt `nginx-blinc.puthipiroj.com.conf` (plus
`nginx-posthoc-locations.conf`) to your hostname and ports, add it to nginx's
`http {}` context, then:

```bash
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your.domain      # HTTPS is required for mic/camera capture
```

### 9. First user

```bash
cd src/server && ../venv-unified/bin/python create_user.py
```

Log in at your domain and create a session.

## Development

Most PRs touch the frontend, the Flask routes or the analytics, and none of
that needs a GPU: the CI checks run on a plain laptop, and so does the API
server with the frontend dev server in front of it. Only the audio and video
processors need the CUDA machine.

### The checks CI runs

Python 3.11 or newer and Node 24 (the version CI uses):

```bash
python3 -m venv .venv-ci
.venv-ci/bin/pip install pytest ruff==0.16.2 numpy scipy flask==3.1.3 requests==2.34.2 prometheus_client==0.25.0 moviepy==2.2.1
.venv-ci/bin/python -m pytest tests/ -q        # unit + contract tests, no DB or GPU
.venv-ci/bin/ruff check src                    # must report no violations
cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build
```

The fifth check, the migration round trip against a real MySQL, needs the
containers from the next section and an empty database:

```bash
docker compose -f deploy/dev/docker-compose.yml exec mysql mysql -uroot -proot -e 'CREATE DATABASE IF NOT EXISTS blinc'
DC_DATABASE_URL=mysql+mysqlconnector://root:root@127.0.0.1:3306/blinc src/venv-server/bin/python src/server/migrations/run_migrations.py roundtrip
```

### GPU memory and the post-hoc services

One 48 GB card serves the live classes, the two post-hoc services, llama-server and whatever experiment is running, so the post-hoc services claim GPU memory only while a run is on:

- Model weights load on the first run, not at start-up (`src/video_processing/server_posthoc.py` `_load_once`, `src/audio_processing/server_posthoc.py` `get_semantic_model`). A freshly started service holds nothing on the card.
- A service with no run for `DC_POSTHOC_IDLE_RECYCLE_S` seconds (default 180) exits and systemd restarts it. Exiting is the one way every CUDA allocation (PyTorch's cache, CTranslate2, cuDNN workspaces) comes back; the audio service used to keep ~9 GB and the video service 13 GB between runs. The queue treats a refused connection during the restart as "retry in 20 s" (`posthoc_queue._ServiceUnavailable`), not as a failed pod.
- Before loading, a run checks the card's free memory with `nvidia-smi` (every process counted) against `DC_AUDIO_POSTHOC_MIN_FREE_MIB` (8192) or `DC_VIDEO_POSTHOC_MIN_FREE_MIB` (14336). A short card hands the GPU lease back and the run defers with the usual `gpu_busy` reply instead of dying in a CUDA OOM beside llama-server (`gpu_lease.acquire_for_run(min_free_mib=...)`).

### Running the site without a GPU

```bash
# 1. MySQL and Redis in Docker. The data lives in a named volume and
#    survives restarts; `down -v` wipes it.
docker compose -f deploy/dev/docker-compose.yml up -d

# 2. A server-only Python environment: Flask, the MySQL driver and what the
#    routes import. About 1 GB, no CUDA. Python 3.11 to 3.13.
python3 -m venv src/venv-server
src/venv-server/bin/pip install -r src/requirements-server.txt

# 3. Configuration. The example already matches the containers (user blinc,
#    database discussion_capture, localhost ports). Set root_dir to a
#    directory you can write to; uploads and voice prints go there.
cp src/server/config.ini.example src/server/config.ini
mkdir -p ~/blinc-data        # then root_dir=/home/<you>/blinc-data in config.ini

# 4. Schema, then a first login (role 2 = admin).
(cd src/server && ../venv-server/bin/flask --app discussion_capture db upgrade)
(cd src/server && ../venv-server/bin/python create_user.py)

# 5. Run. Vite proxies /api and /socket.io to :5001 (frontend/vite.config.js).
DC_PORT=5001 src/venv-server/bin/python src/server/discussion_capture.py
cd frontend && npm ci && npm start              # http://localhost:3000
```

Everything the browser asks the Flask server for works: sign-in, sessions,
People and Students, the dashboard pages, every `/api` route. Nothing that
needs a processor does: live capture, voice enrollment, transcription, video,
post-hoc runs. Gemini requests fail until a real `GOOGLE_API_KEY` is in
`src/server/.env`; the server starts without one.

If a MySQL or Redis already listens on this machine, start the containers on
other ports and point the server at them:

```bash
BLINC_MYSQL_PORT=3307 BLINC_REDIS_PORT=6380 docker compose -f deploy/dev/docker-compose.yml up -d
# in config.ini: database_port=3307 and redis_port=6380
DC_PORT=5091 DC_DEVICE_WS_PORT=9091 src/venv-server/bin/python src/server/discussion_capture.py
cd frontend && DC_API_TARGET=http://localhost:5091 npm start
```

### Processors by hand

On the GPU machine, run any processor from the unified venv the same way
(stop its systemd unit first):

```bash
src/venv-unified/bin/python src/audio_processing/server.py
src/venv-unified/bin/python src/audio_processing/server_posthoc.py
export PYTHONPATH=src/video_processing:src/video_processing/yolo_head   # video only
src/venv-unified/bin/python src/video_processing/server.py
src/venv-unified/bin/python src/video_processing/server_posthoc.py
```

**Mic/camera over plain HTTP** (LAN testing): Chrome blocks capture on
insecure origins. Add your server's address at
`chrome://flags/#unsafely-treat-insecure-origin-as-secure` and relaunch.

### Optional components

- **CrisperWhisper** post-hoc ASR runs in its own venv (its CTranslate2 fork
  would shadow the real one): build `src/venv-crisper` from
  `src/requirements-crisper.txt`.
### MOSS end to end (the default post-hoc engine)

The default post-hoc run is [MOSS-Transcribe-Diarize](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize) (OpenMOSS 0.9B, Apache-2.0): one model listens to the whole recording and writes timestamped, speaker-labelled, punctuated turns, so there is no separate diarizer, aligner or word-assignment step. Its labels (S01, S02, ...) are named against the enrolled voice prints by `asr_connectors/moss_naming.py` (Naming, below).

- Engine: `src/audio_processing/asr_connectors/moss_asr.py` runs `moss_cli.py` in `src/venv-granite` (transformers 5.x, the OpenMOSS package from `~/src/MOSS-Transcribe-Diarize`, Triton) through `moss_run.py`.
- The decode loop is our own (`moss_cli.py`): the model in bf16 (Qwen3's MLP overflows fp16 on an hour of audio and emits only "!"), a pre-allocated fp16 KV cache, a Triton split-key kernel for the single-query step (`triton_decode.py`), the step replayed as a CUDA graph, and the vocabulary projection in fp32. On the Quadro RTX 8000 (Turing) it does about 42 tokens/s, an hour of audio in 16 minutes; HF generate managed 2 to 3.
- Turing GPUs have no PyTorch flash attention; `flash_turing_attn.py` registers the [flash-attention-turing](https://github.com/ssiu/flash-attention-turing) port as the `turing_fa` backend for the encoder and prefill. Build it once into the venv: clone to `~/src/flash-attention-turing` (or set `FLASH_ATTENTION_TURING_DIR`), then `MAX_JOBS=4 src/venv-granite/bin/pip install -v . --no-build-isolation` (about 6 minutes). On an Ampere-or-newer GPU the loop runs on PyTorch's own kernels without it.
- Budget: the cache is sized at launch for `--max-new-tokens` (default 40,000, about 10 tokens per audio second); a recording past 70 minutes needs a larger value. Progress is written to `<out>.progress` while a pass runs.
- Naming (`asr_connectors/moss_naming.py`): MOSS's labels (S01, S02, ...) are named against the students' voice prints of both laptops of the group. A student's print is the enrolment print when there is one, else a print cut from the student's confidently named live rows on this recording (the API's `callback/naming_rows/<key>` hands the connector both pods' rows before the run's rows are wiped). A cluster is named on up to 120 s of its longest turns; the best print wins above its kind's floor (0.35 enrolment, 0.60 session) and by a 0.06 margin; the side (own laptop or across the table) comes from the prints or the live rows' majority; one printless student on a side takes the largest unnamed cluster on it. The processor keeps these names (`named_by_asr`) instead of re-checking each piece against the prints.
- Measured on the Viking class, Group 7 (2026-10-18): 94% of speech named on both laptops, 19 unnamed merged lines against 50 to 71 for the other engines, punctuation and no doubled words; cross-laptop agreement 83%, a little under the diarizer-plus-recognizer pairs.

  **DiariZen** (the default, `src/venv-diarizen`) and **Nemotron-3**
  (`src/venv-nemo3`); build recipes, model ids and licences in
  `src/requirements-unified.README.md`. When one fails the audio service
  runs the other.
- None is needed unless you select those backends.

## TODO

- [ ] Audit and update outdated dependencies across all components (frontend npm packages, server/audio/video Python packages). Stale Dependabot PRs were closed — dependency updates will be handled as a coordinated batch effort.
- [ ] Set up CI/CD pipeline (testing, linting, automated checks).
- [ ] Decide whether the anonymous student-dashboard / expert-rating surface needs a credential. Those flows (no accounts, no processing key) still read transcripts, synthesized feedback, and LLM answers through the passcode/alias routes — each is marked "open by design" in the route comments. Tightening it means minting a token from the passcode (or similar) that those flows can hold; a login gate would break them.
- [ ] Pod processing keys appear in nginx access logs via the `?key=` query param that `<video>`/`<img>` tags use to authenticate against the guarded device endpoints. Either accept (keys are per-pod and short-lived), scrub the param from nginx's log format, or rotate keys on session end.
