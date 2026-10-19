# Unified production environment

One Python 3.13 venv (`src/venv-unified`) runs every BLINC component: the
Flask web server, the coordinator and the audio/video live + post-hoc
processors. (The MOSS engine runs as a subprocess in `src/venv-granite`, the
live CrisperWhisper worker in `src/venv-crisper`.) Rebuild with:

    /home/vlj9405/miniforge3/envs/py313/bin/python3.13 -m venv src/venv-unified
    src/venv-unified/bin/pip install -r src/requirements-unified.txt --extra-index-url https://download.pytorch.org/whl/cu128
    src/venv-unified/bin/pip install git+https://github.com/fkryan/gazelle
    src/venv-unified/bin/python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

Build it beside the running one (`src/venv-unified-next`), check `pip check`
and the imports, then swap the directories and restart the services; the old
one stays as `src/venv-unified-prev` until the swap has proved itself.

Hard pins and why:
- torch/torchaudio/torchvision 2.11.0 via the cu128 index
  (https://download.pytorch.org/whl/cu128) — PyPI's default wheels moved to
  CUDA 13, which the 570 driver cannot run; the cu128 builds are current and
  include Turing (sm_75) kernels. torchcodec must also come from that index.
- transformers 5.20.1, tokenizers 0.23.3, huggingface_hub 2.2.0, accelerate
  1.15.0 — the generation the MOSS engine runs on (`src/venv-granite` has the
  same), moved to on 2026-10-19 once the Qwen3-ASR package, which pinned
  transformers to exactly 4.57.6, was dropped (the Qwen3 connector itself
  was removed the same day).
- numpy 2.x — py3.13 has no numpy 1.x wheels; gensim>=4.4 accepts numpy 2.
- Gaze-LLE's DINOv2 backbone loads via torch.hub; the hub cache pins
  facebookresearch/dinov2 to a revision without py3.10-only syntax issues
  (any revision works on py3.10+).

Everything else floats at the latest release as of 2026-07 (Flask 3.1,
Flask-SocketIO 5.6 — requires the frontend's socket.io-client v4 — SQLAlchemy
2.0, gensim 4.4, google-cloud-speech 2.40, moviepy 2.2, ultralytics 8.4).

## Post-hoc speakers

The post-hoc engine is MOSS (`src/venv-granite`), which labels the speakers
as it transcribes and names them from the enrolled voice prints; the
provenance names `moss`. A CrisperWhisper re-run matches each utterance
against the prints (`fingerprint`). The WhisperX engine, its DiariZen and
Nemotron-3 diarizers and their venvs (`src/venv-diarizen`, `src/venv-nemo3`,
Sortformer's `src/venv-nemo`) were removed on 2026-10-19; whisperx,
faster-whisper, ctranslate2 and the pyannote packages left this environment
with them (an installed venv keeps them until it is rebuilt).
