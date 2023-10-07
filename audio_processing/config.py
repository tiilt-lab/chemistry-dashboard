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

def video_record_original():
    return str(config['videorecord']['original']) in ['true', 'True', 't', '1']

def video_record_reduced():
    return str(config['videorecord']['reduced']) in ['true', 'True', 't', '1']

def video_recordings_folder():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), str(config['videorecord']['video_recording_folder']))

def asr():
    return str(config['processing']['asr'])

def keyword_model_limit():
    return int(config['processing']['keyword_model_limit'])

def processing_callback():
    return str(config['output']['processing_callback'])

def tagging_callback():
    return str(config['output']['tagging_callback'])

def connect_callback():
    return str(config['output']['connect_callback'])

def disconnect_callback():
    return str(config['output']['disconnect_callback'])

def root_dir():
    return str(config['rootpath']['root_dir'])