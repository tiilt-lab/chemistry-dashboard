# Unified production environment

One Python 3.10 venv (`src/venv-unified`) runs every BLINC component: the
Flask web server, the audio/video live + post-hoc processors and the Qwen3-ASR
worker. Rebuild with:

    /home/vlj9405/miniforge3/bin/python3.10 -m venv src/venv-unified
    src/venv-unified/bin/pip install -r src/requirements-unified.txt
    src/venv-unified/bin/pip install <local clone of github.com/fkryan/gazelle>
    src/venv-unified/bin/python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

Hard pins and why:
- torch/torchaudio/torchvision 2.8.0 — newest supporting the installed CUDA
  12.8 driver (2.10+ wheels require a newer driver).
- transformers 4.57.6 — pinned by qwen-asr.
- numpy 1.26.4 — gensim 4.x requires numpy<2.
- Gaze-LLE's DINOv2 backbone loads via torch.hub; the hub cache pins
  facebookresearch/dinov2 to a revision without py3.10-only syntax issues
  (any revision works on py3.10+).

Everything else floats at the latest release as of 2026-07 (Flask 3.1,
Flask-SocketIO 5.6 — requires the frontend's socket.io-client v4 — SQLAlchemy
2.0, gensim 4.4, google-cloud-speech 2.40, moviepy 2.2, ultralytics 8.4).
