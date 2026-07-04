# Unified production environment

One Python 3.13 venv (`src/venv-unified`) runs every BLINC component: the
Flask web server, the audio/video live + post-hoc processors and the Qwen3-ASR
worker. Rebuild with:

    /home/vlj9405/miniforge3/envs/py313/bin/python3.13 -m venv src/venv-unified
    src/venv-unified/bin/pip install -r src/requirements-unified.txt
    src/venv-unified/bin/pip install <local clone of github.com/fkryan/gazelle>
    src/venv-unified/bin/python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

Hard pins and why:
- torch/torchaudio/torchvision 2.11.0 via the cu128 index
  (https://download.pytorch.org/whl/cu128) — PyPI's default wheels moved to
  CUDA 13, which the 570 driver cannot run; the cu128 builds are current and
  include Turing (sm_75) kernels. torchcodec must also come from that index.
- transformers 4.57.6 — pinned by qwen-asr.
- numpy 2.x — py3.13 has no numpy 1.x wheels; gensim>=4.4 accepts numpy 2.
- Gaze-LLE's DINOv2 backbone loads via torch.hub; the hub cache pins
  facebookresearch/dinov2 to a revision without py3.10-only syntax issues
  (any revision works on py3.10+).

Everything else floats at the latest release as of 2026-07 (Flask 3.1,
Flask-SocketIO 5.6 — requires the frontend's socket.io-client v4 — SQLAlchemy
2.0, gensim 4.4, google-cloud-speech 2.40, moviepy 2.2, ultralytics 8.4).
