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

## DiariZen diarization venv (`src/venv-diarizen`)

The post-hoc audio analysis diarizes with DiariZen by default
(`diarizer: diarizen`, model `BUT-FIT/diarizen-wavlm-large-s80-md-v2`:
WavLM-based, overlap-aware). Like Sortformer's `src/venv-nemo`, it needs its
own environment — DiariZen pins torch 2.1 and ships a pyannote.audio 3.1.1
fork that cannot share a venv with whisperx — so the audio service runs
`src/audio_processing/asr_connectors/diarizen_cli.py` as a subprocess
(`diarizen_diar.py`) and falls back to pyannote 3.1 when the venv or model is
missing. Built 2026-10-18 from a checkout of github.com/BUTSpeechFIT/DiariZen:

    python3.10 -m venv src/venv-diarizen
    src/venv-diarizen/bin/pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 \
        --index-url https://download.pytorch.org/whl/cu121
    cd <DiariZen checkout>
    pip install -r requirements.txt -c constraints.txt && pip install -e . -c constraints.txt
    cd pyannote-audio && pip install -e . -c ../constraints.txt

(the jupyterlab, pre-commit, tensorboard, matplotlib and openpyxl entries of
DiariZen's requirements.txt were skipped — tooling, not inference). The model
and its `pyannote/wespeaker-voxceleb-resnet34-LM` embedder come from the
Hugging Face cache; the subprocess runs with `HF_HUB_OFFLINE=1`, so download
both once with network before the first run.

Licence: the DiariZen code is MIT, but the checkpoint weights are
**CC BY-NC 4.0 — research use only**. Cost: 58.7 min of 16 kHz mono audio in
273 s on the Quadro RTX 8000 at batch 16 (5.8 GB GPU peak; 11 GB at
DiariZen's default batch 32); `max_speakers` is capped at 8 for a pod.
