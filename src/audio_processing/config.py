import configparser
import os

def initialize():
    global config
    config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.ini'
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(config_path)

    # Create recordings folder
    if record_original() or record_reduced():
        if not os.path.isdir(recordings_folder()):
            os.mkdir(recordings_folder())

def record_original():
    return str(config['record']['original']) in ['true', 'True', 't', '1']

def record_reduced():
    return str(config['record']['reduced']) in ['true', 'True', 't', '1']

def recordings_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['record']['recording_folder']))

def biometric_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['biometrics']['biometrics_folder']))

def video_record_original():
    return str(config['videorecord']['original']) in ['true', 'True', 't', '1']

def video_record_reduced():
    return str(config['videorecord']['reduced']) in ['true', 'True', 't', '1']

def video_cartoonize():
    return str(config['videocartoonize']['cartoonize']) in ['true', 'True', 't', '1']

def video_recordings_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['videorecord']['video_recording_folder']))

def asr():
    return str(config['processing']['asr'])

def scorer():
    # Expression & Thinking Style backend: 'liwc' (default) or 'llm'.
    return str(config['processing'].get('scorer', 'liwc'))

def semantic_embedder():
    # Sentence embedder for participation/cohesion metrics on the LIVE path.
    # 'all-mpnet-base-v2' (default: light, comparable with historical metrics)
    # or 'bge-large-en-v1.5' to match the post-hoc default.
    # Self-inits because server.py resolves this at import time, before main()
    # calls initialize().
    if 'config' not in globals():
        initialize()
    return str(config.get('processing', 'semantic_embedder', fallback='all-mpnet-base-v2'))

def diarization_fallback():
    # How the post-hoc fallback (no-fingerprint) path assigns speaker clusters.
    # Distinct from the per-run payload 'diarizer' (fingerprint|pyannote), which
    # decides whether the ASR *runs* pyannote; this decides what the fallback
    # clustering *does with* any labels the ASR produced:
    #   'spectral' (default) -- the original ECAPA + spectral clustering.
    #   'pyannote'           -- reuse pyannote 3.1 cluster labels already
    #                           attached by batch ASR (WhisperX/Qwen3); falls
    #                           back to spectral when labels are absent.
    return str(config.get('processing', 'diarization_fallback', fallback='spectral'))

def whisper_model_size():
    return str(config.get('whisper', 'model_size', fallback='small.en'))

def whisper_device():
    return str(config.get('whisper', 'device', fallback='auto'))

def whisper_compute_type():
    return str(config.get('whisper', 'compute_type', fallback='int8'))

def keyword_model_limit():
    return int(config['processing']['keyword_model_limit'])

def topic_backend():
    # Topic-modeling backend: 'lda' (default; the pre-trained per-owner gensim
    # LDA model, active only when a run supplies topic_model) or 'bertopic'
    # (fits on the session's transcripts using the loaded BGE embeddings — the
    # practical re-enable of topic modeling; requires `pip install bertopic`).
    return str(config.get('processing', 'topic_backend', fallback='lda'))

def keyword_backend():
    # Keyword semantic-matching backend: 'word2vec' (2013 GoogleNews-300,
    # default) or 'embedding' (a modern SentenceTransformer, see
    # keyword_embedding_model).
    return str(config.get('processing', 'keyword_backend', fallback='word2vec'))

def keyword_embedding_model():
    # SentenceTransformer used when keyword_backend='embedding'.
    return str(config.get('processing', 'keyword_embedding_model',
                          fallback='BAAI/bge-small-en-v1.5'))

def keyword_embedding_threshold():
    # Cosine-distance cutoff for the embedding backend (lower = stricter).
    # Tighter than the word2vec 0.6 because sentence-embedding distances are
    # compressed into a higher band.
    return float(config.get('processing', 'keyword_embedding_threshold',
                            fallback='0.28'))

def processing_callback():
    return str(config['output']['processing_callback'])

def tagging_callback():
    return str(config['output']['tagging_callback'])

def connect_callback():
    return str(config['output']['connect_callback'])

def disconnect_callback():
    return str(config['output']['disconnect_callback'])

def cartoonize_image_callback():
    return str(config['output']['cartoonize_image_callback'])

def root_dir():
    return str(config['rootpath']['root_dir'])

def speaker_metrics_callback():
    return str(config['output']['speaker_metrics_callback'])

def redis_host():
    return str(config.get('redis', 'redis_host', fallback='localhost'))

def redis_port():
    return int(config.get('redis', 'redis_port', fallback=6379))

def redis_db():
    return int(config.get('redis', 'redis_db', fallback=0))
