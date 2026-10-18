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

## Post-hoc diarizers

The post-hoc audio analysis offers exactly two speaker diarizers, `diarizen`
(the default) and `nemotron3`. Each runs in its own venv as a subprocess of
the audio service (`src/audio_processing/asr_connectors/*_cli.py` behind
`*_diar.py`), and when the chosen one fails the service runs the other; if
both fail the run fails (`posthoc_failed`, previous results kept). The
provenance stored with the pod names the one that actually ran. To change
the default, flip `DIARIZER_DEFAULT` in
`frontend/src/components/posthoc/posthoc-trigger.jsx` and the
`models.get("diarizer", ...)` default in `src/server/posthoc_queue.py`.

### DiariZen diarization venv (`src/venv-diarizen`)

`diarizer: diarizen`, model `BUT-FIT/diarizen-wavlm-large-s80-md-v2`
(WavLM-based, overlap-aware). Like Sortformer's `src/venv-nemo`, it needs its
own environment — DiariZen pins torch 2.1 and ships a pyannote.audio 3.1.1
fork that cannot share a venv with whisperx. Built 2026-10-18 from a checkout
of github.com/BUTSpeechFIT/DiariZen:

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

### Nemotron-3 diarization venv (`src/venv-nemo3`)

`diarizer: nemotron3`, model `nvidia/Nemotron-3-Diarization` (streaming
Sortformer, up to 8 speakers; the post-hoc CLI applies the model card's
offline "very high latency" preset: spkcache_len 264, fifo_len 40, chunk_len
340, chunk_right_context 40, spkcache_update_period 300). The checkpoint's
transformer encoder uses `self_attention_model='rope'`, which the PyPI NeMo
3.0.0 release cannot load — and neither can the production `src/venv-nemo`
(NeMo 2.7.3, Sortformer) — so NeMo comes from GitHub main (the installed
version reports 3.1.0+a3afbd901). Built 2026-10-18:

    python3.10 -m venv src/venv-nemo3
    src/venv-nemo3/bin/pip install torch==2.11.0 torchaudio==2.11.0 \
        --index-url https://download.pytorch.org/whl/cu128
    src/venv-nemo3/bin/pip install "nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git@main"

The checkpoint comes from the Hugging Face cache; the subprocess runs with
`HF_HUB_OFFLINE=1`, so download it once with network before the first run.

Licence: **OpenMDW-1.1** (commercial use allowed). Cost: the 3 min test
slice in 11.8 s with a 579 MiB GPU peak — far faster than real time.
