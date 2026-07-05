import configparser
import os

def initialize():
    global config
    config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.ini'
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read(config_path)

    # Create recordings folder
    if video_record_original() or video_record_reduced():
        if not os.path.isdir(video_recordings_folder()):
            os.mkdir(video_recordings_folder())


def video_record_original():
    return str(config['videorecord']['original']) in ['true', 'True', 't', '1']

def video_record_reduced():
    return str(config['videorecord']['reduced']) in ['true', 'True', 't', '1']

def video_cartoonize():
    return str(config['videocartoonize']['cartoonize']) in ['true', 'True', 't', '1']

def process_video_analytics():
    return str(config['videoanalyics']['processvideoanalytics']) in ['true', 'True', 't', '1']
    
def video_recordings_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['videorecord']['video_recording_folder']))

def facial_embedding_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['facialembedding']['facial_embedding_folder']))

def host_server_address():
    return str(config['output']['host_server_address'])

def listening_port():
    return str(config['output']['listening_port'])

def cartoonize_image_callback():
    return str(config['output']['cartoonize_image_callback'])

def root_dir():
    return str(config['rootpath']['root_dir'])

def redis_session_key_callback():
    return str(config['output']['redis_get_session_key_callback'])

def redis_session_config_callback():
    return str(config['output']['redis_get_session_config_callback']) 

def video_metrics_callback():
    return str(config['output']['video_metrics_callback'])

def connect_callback():
    return str(config['output']['connect_callback'])

def disconnect_callback():
    return str(config['output']['disconnect_callback'])

def redis_host():
    return str(config.get('redis', 'redis_host', fallback='localhost'))

def redis_port():
    return int(config.get('redis', 'redis_port', fallback=6379))

def redis_db():
    return int(config.get('redis', 'redis_db', fallback=0))
def emotion_model():
    # Facial-emotion backend: 'resmasking' (FER-2013, default) or 'hsemotion'
    # (EfficientNet-B2 on AffectNet-8 via ONNX — the open SOTA option).
    # Self-initializes because the servers select the model at import time,
    # before main() calls initialize().
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'emotion_model', fallback='resmasking'))

def object_model():
    # Object-of-focus detector: 'yolo11' (open SOTA, ultralytics) or 'yolov4'
    # (the original YOLOv4-P7 weights). Read at server start.
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'object_model', fallback='yolo11'))

def head_model():
    # Head/person detector: 'yolov5' (the vendored yolo_head CrowdHuman
    # YOLOv5m, default) or 'ultralytics' (a YOLO11/YOLOv8 head model loaded via
    # the ultralytics package — set head_weights). Moving to 'ultralytics' is
    # what allows retiring the vendored yolo_head/ repo. No official
    # CrowdHuman-YOLO11 checkpoint exists yet; supply your own weights.
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'head_model', fallback='yolov5'))

def head_weights():
    # Weights file for head_model='ultralytics' (e.g. a CrowdHuman-trained
    # YOLOv8/YOLO11 .pt). Relative to attention_tracking/.
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'head_weights',
                          fallback='crowdhuman_yolov8m_head.pt'))

def person_of_focus():
    # When a gaze target is a recognized head, record it as 'person:<alias>'
    # (mutual-gaze / who-looks-at-whom) instead of a generic label. Off by
    # default because it changes stored object_on_focus values; needs a re-run.
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'person_of_focus', fallback='false')) in ['true', 'True', 't', '1']

def face_model():
    # Face detection + embedding backend: 'dlib' (face_recognition 128-D,
    # default) or 'insightface' (ArcFace buffalo_l 512-D, open SOTA). Switching
    # requires re-enrolling students and using ArcFace thresholds — see
    # facial_recognition_backend.py.
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'face_model', fallback='dlib'))

def attention_model():
    # Gaze/attention backend: 'gazelle' (Gaze-LLE, open SOTA, default) or
    # 'gazefollow' (the 2020 ModelSpatial weights).
    if 'config' not in globals():
        initialize()
    return str(config.get('videoprocessing', 'attention_model', fallback='gazelle'))

def posthoc_fps():
    # Frames per second sampled by the post-hoc video pipeline. 12 matches the
    # original behaviour; lower it (e.g. 6) to halve processing time when
    # coarse attention/emotion trends are enough.
    if 'config' not in globals():
        initialize()
    return int(config.get('videoprocessing', 'posthoc_fps', fallback=12))
