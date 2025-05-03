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

def attention_tracking():
    return str(config['attentiontracking']['attentiontracking']) in ['true', 'True', 't', '1']

def video_recordings_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['videorecord']['video_recording_folder']))

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