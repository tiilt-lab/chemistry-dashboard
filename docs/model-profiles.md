# Model configuration & post-hoc vs. live profiles

This project runs the same analyses in two contexts with deliberately different
model choices:

- **Live profile** — the real-time path (`server.py` services). Optimised for
  latency and comparability with historical metrics. Conservative defaults.
- **Post-hoc profile** — batch re-analysis (`server_posthoc.py` services,
  triggered from the post-hoc UI). Latency-tolerant, so it defaults to the
  open-SOTA stack. Users can also override models **per run** from the trigger
  UI.

Because the two profiles diverge on purpose, the defaults live in three places.
This is the single source of truth for what they should be.

## Where a value comes from (precedence)

For a post-hoc run, each model choice is resolved as:

1. **Per-run payload field** (from the trigger UI) — highest priority.
2. **`config.ini`** for that service — deployment default.
3. **Code fallback** in `config.py` — last resort if the key is absent.

The live path uses only (2) and (3). Keep the code fallback equal to the
intended default so behaviour is predictable when a key is missing.

## Audio (`src/audio_processing/`)

| Knob | config.ini `[processing]` | Code fallback | Per-run field | Live default | Post-hoc default (UI) |
|---|---|---|---|---|---|
| ASR | `asr` | `google-cloud-speech` | `asr` | google-cloud-speech | **whisperx** |
| E&T scorer | `scorer` | `liwc` | `scorer` | liwc | liwc |
| Speaker ID | — | — | `diarizer` (fingerprint\|pyannote) | fingerprint | **pyannote** |
| Cohesion embedder | `semantic_embedder` | `all-mpnet-base-v2` | `embedder` | all-mpnet-base-v2 | **bge-large-en-v1.5** |
| Keyword matching | `keyword_backend` | `word2vec` | — | **embedding** (set in ini) | embedding |
| Fallback clustering | `diarization_fallback` | `spectral` | — | **pyannote** (set in ini) | pyannote |
| Whisper size | `[whisper] model_size` | `small.en` | — | **large-v3** (set in ini) | large-v3 |
| Topic modeling | `topic_backend` | `lda` (dormant unless `topic_model` supplied) | `topic_model` | off | off (set `bertopic` to enable) |

Per-analysis toggles (post-hoc full run, default all on): `run_transcribe`,
`run_features`, `run_doa`, `run_tagging`.

## Video (`src/video_processing/`)

| Knob | config.ini `[videoprocessing]` | Code fallback | Per-run field |
|---|---|---|---|
| Emotion | `emotion_model` | `hsemotion` | `emotion_model` |
| Object of focus | `object_model` | `yolo11` | — (config only) |
| Gaze/attention | `attention_model` | `gazelle` | `attention_model` |
| Face recognition | `face_model` | `dlib` | — (config only) |
| Head detector | `head_model` | `yolov5` | — (config only) |
| Sampling rate | `posthoc_fps` | `12` | — (config only) |

Emotion and attention are per-run selectable (lazy per-name model cache in
`server_posthoc.py`). The object/face/head detector is the heavy,
CUDA-lock-serialised model shared across concurrent runs, so it stays
config-level.

## Provenance

Each post-hoc run records the resolved model choice set. The audio/video
servers build `self.model_choices`; the frontend posts it to
`POST /api/v1/sessions/<id>/device/<id>/posthoc_completed` as `{ "models": ... }`,
and it is stored on `session_device.posthoc_models` (nullable JSON text).
`GET /api/v1/models` reports the *current* config-resolved stack with
human-readable labels.

## Enabling the optional SOTA backends

| Backend | Enable | Prerequisite |
|---|---|---|
| InsightFace face recognition | `face_model=insightface` | `pip install insightface onnxruntime-gpu`; re-enrol all students (512-D galleries) |
| Ultralytics head detector | `head_model=ultralytics` + `head_weights=<file>` | supply a CrowdHuman YOLO11/YOLOv8 `.pt` |
| BERTopic topic modeling | `topic_backend=bertopic` | `pip install bertopic` |
| bge-large live embedder | `semantic_embedder=bge-large-en-v1.5` | none (already cached) |
