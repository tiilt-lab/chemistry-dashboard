import os
import json
import time
import logging
import wave
import scipy.signal
import config as cf
import numpy as np
import soundfile as sf
import traceback
from queue import Queue
from pathlib import Path
from scipy.io import wavfile
from recorder import VidRecorder
from processor_posthoc import AudioProcessorPosthoc
from processor_speaker_metric import SpeakerMetricProcessor
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager
from audio_buffer import AudioBuffer
from audio_stream_reader import AudioStreamReader
from asr_connectors.google_asr_connector_posthoc import GoogleASR
from twisted.internet import reactor, task
from features_detector import features_detector
from keyword_detector import keyword_detector
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from speechbrain.inference import SpeakerRecognition
from sentence_transformers import SentenceTransformer

cm = ConnectionManager()
semantic_model = SentenceTransformer("all-mpnet-base-v2")
diarization_model = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/pretrained_ecapa")
semantic_model.share_memory()
STOP_SIGNAL = object()

running_audio_processes = {}

class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_message = time.time()
        self.stream_data = False
        self.interval = 10
        # Only the full-audio-analytics path (signal_start) creates these; the
        # transcript-only P&I / E&T operations never do, so default them so
        # signal_end / onClose cleanup doesn't crash on an unset attribute.
        self.asr = None
        self.processor = None
        self.audioreader = None
        self.processorspeakermetric = None
        self.config = None
        # Consulted by the connection manager's periodic key check; posthoc
        # connections aren't live-key gated, so leave it false.
        self.running = False

        cm.add(self)
        logging.info('New client connected...')

    def onMessage(self, payload, is_binary):
        self.last_message = time.time()
        if is_binary:
            try:
                self.process_binary(payload)
            except Exception as e:
                logging.warning('Error processing binary: {0}'.format(e))
        else:
            valid_json = False
            try:
                payload = payload.decode('utf-8')
                data = json.loads(payload)
                valid_json = True
            except Exception as e:
                logging.warning('Payload is not properly formatted JSON.')
                self.send_json({'type': 'error', 'message': 'Payload is not properly formatted JSON.'})
            if valid_json:
                try:
                    self.process_json(data)
                except Exception as e:
                    logging.warning('Error processing json: {0}'.format(e))

    def onClose(self, wasClean, code, reason):
        logging.info("close was trigered externally..... wasclean {0}, code {1}, reason {2}".format( wasClean, code, reason))
        self.signal_end()

    def process_json(self, data):
        if not 'type' in data:
            logging.warning('Message does not contain "type".')
            return
        
        if data['type'] == 'Initialize_audio_processing_analytics':
            self.sessionid = data['sessionid']
            self.session_device_id = data['sessiondeviceid']
            self.server_start= data['server_start']
            self.keywords= data['keywords']
            # Optional per-run model choices from the trigger UI; fall back to
            # the deployment config when absent.
            self.asr_choice = data.get('asr') or cf.asr()
            self.scorer_choice = data.get('scorer') or None
            self.diarizer_choice = data.get('diarizer') or 'fingerprint'
            self.speakers = dict()
            self.stream_data = "audio"
            self.buffer_size = 4096
            self.sample_rate = 16000
            self.queue_put_timeout = 0.05
            self.audio_file = self.get_audio_file_path(self.session_device_id)

            if not self.audio_file:
                self.send_json({'type': 'error', 'message': 'No audio captured for this group.'})
            else:
                self.audio_file = str(self.audio_file)
                file_path_split = self.audio_file.split("(")
                key = file_path_split[0].split("/")[-1]
                off_set_date = file_path_split[1].split(")")[0]
 
                 #keep track of currently running posthoc video analytics
                if key in running_audio_processes:
                    self.send_json({'type': 'error', 'message': 'Audio posthoc analytics for this group is already running'})

                running_audio_processes[key] = "running"

                conf_val = {'key':key,'encoding': "pcm_f32le", 'sample_rate': self.sample_rate,'channels': 1,'sessionid': self.sessionid,'deviceid': self.session_device_id,
                            'tag': True, 'server_start':self.server_start,'keywords':self.keywords,'transcribe':True,'features':True,'doa':True,'topic_model':None,'owner':1,'off_set_date':off_set_date}
                valid, result = ProcessingConfig.from_json(conf_val,source="posthoc processing")
                if not valid:
                    logging.info("Confgiration setting failed for audio posthoc processing")
                else:    
                    self.config = result
                    
                    if os.path.splitext(self.audio_file)[1] == ".dat":
                        wavfilename =  os.path.splitext(self.audio_file)[0]+".wav"
                        with open(self.audio_file, "rb") as f:
                            all_data = f.read()
                            all_data = np.frombuffer(all_data, np.float32 if self.config.depth == 4 else np.int16, -1)
                            chunk_length = int(len(all_data) / self.config.channels)
                            all_data = np.reshape(all_data, (chunk_length, self.config.channels))
                        wavfile.write(wavfilename, self.config.sample_rate, all_data)
                        os.remove(self.audio_file)
                        self.audio_file = wavfilename
                        

                    #start processing
                    for speaker in data['speakers']:
                        audio_fingerprint_file = os.path.join(cf.biometric_folder(), "{0}".format(speaker["alias"]))
                        wavObj = wave.open(audio_fingerprint_file+'.wav')
                        byte_audio_data = self.read_bytes_from_wav(wavObj) 
                        self.speakers[speaker["id"]] = {"alias": speaker["alias"], "data": byte_audio_data}

                    self.signal_start()
                    self.processor.setSpeakerFingerprints(self.speakers)

                    self.send_json({'type':'init posthoc analytics completed','message':"Starting Audio Analytics Processing"})
                    logging.info('Audio Posthoc analytics initiated')

        if data['type'] == 'Initialize_participation_and_impact_style_computation':
            self.sessionid = data['sessionid']
            self.session_device_id = data['sessiondeviceid']
            self.server_start= data['server_start']
            self.keywords= data['keywords'] 
            self.transcript = data["transcript"]
            self.sample_rate = 16000
            self.speakers = dict()

            self.audio_file = self.get_audio_file_path(self.session_device_id)

            if self.audio_file:
                self.audio_file = str(self.audio_file)
                file_path_split = self.audio_file.split("(")
                key = file_path_split[0].split("/")[-1]
                off_set_date = file_path_split[1].split(")")[0]
            else:
                key = "No key"
                off_set_date = "Sat Jun 27 18:17:13 2026" #this is just a generic date

                #keep track of currently running posthoc video analytics
            if key in running_audio_processes:
                self.send_json({'type': 'error', 'message': 'Audio posthoc analytics for this group is already running'})

            running_audio_processes[key] = "running"    

            conf_val = {'key':key,'encoding': "pcm_f32le", 'sample_rate': self.sample_rate,'channels': 1,'sessionid': self.sessionid,'deviceid': self.session_device_id,
                            'tag': True, 'server_start':self.server_start,'keywords':self.keywords,'transcribe':True,'features':True,'doa':True,'topic_model':None,'owner':1,'off_set_date':off_set_date}
            valid, result = ProcessingConfig.from_json(conf_val,source="posthoc processing")
            if not valid:
                logging.info("Confgiration setting failed for audio posthoc processing")
            else:    
                self.config = result
                for speaker in data['speakers']:
                    self.speakers[speaker["id"]] = {"alias": speaker["alias"], "id": speaker["id"]}
                self.processorspeakermetric = SpeakerMetricProcessor(self.sessionid, self.session_device_id, self.transcript,semantic_model,self.config,running_audio_processes, scorer=data.get('scorer'))
                self.processorspeakermetric.setSpeakerFingerprints(self.speakers)
                self.send_json({'type':'init participation and impact style completed','message':"Starting Speaker Transcript Metric Processing"})
                logging.info('participation and impact style initiated')

        if data['type'] == 'Initialize_expressing_and_thinking_style_computation':
            self.sessionid = data['sessionid']
            self.session_device_id = data['sessiondeviceid']
            self.server_start= data['server_start']
            self.keywords= data['keywords'] 
            self.transcript = data["transcript"]
            self.sample_rate = 16000
            self.speakers = dict()

            self.audio_file = self.get_audio_file_path(self.session_device_id)

            if not self.audio_file:
                self.send_json({'type': 'error', 'message': 'No audio captured for this group.'})
            else:
                self.audio_file = str(self.audio_file)
                file_path_split = self.audio_file.split("(")
                key = file_path_split[0].split("/")[-1]
                off_set_date = file_path_split[1].split(")")[0]
 
                 #keep track of currently running posthoc video analytics
                if key in running_audio_processes:
                    self.send_json({'type': 'error', 'message': 'Audio posthoc analytics for this group is already running'})

                running_audio_processes[key] = "running"    

                conf_val = {'key':key,'encoding': "pcm_f32le", 'sample_rate': self.sample_rate,'channels': 1,'sessionid': self.sessionid,'deviceid': self.session_device_id,
                                'tag': True, 'server_start':self.server_start,'keywords':self.keywords,'transcribe':True,'features':True,'doa':True,'topic_model':None,'owner':1,'off_set_date':off_set_date}
                valid, result = ProcessingConfig.from_json(conf_val,source="posthoc processing")
                if not valid:
                    logging.info("Confgiration setting failed for audio posthoc processing")
                else:    
                    self.config = result
                    for speaker in data['speakers']:
                        self.speakers[speaker["id"]] = {"alias": speaker["alias"], "id": speaker["id"]}
                    self.processorspeakermetric = SpeakerMetricProcessor(self.sessionid, self.session_device_id, self.transcript,semantic_model,self.config,running_audio_processes, scorer=data.get('scorer'))
                    self.processorspeakermetric.setSpeakerFingerprints(self.speakers)
                    self.send_json({'type':'init expression and thinking style completed','message':"Starting Transcript Metric Processing"})
                    logging.info('Expression and thinking style initiated')

        if data['type'] == 'start_posthoc_audio_processing':
            # start reading audio from wav file and pass to processors
            self.send_json({'type':'audio posthoc analytics started','message':"Processing Audio posthoc Analytics"})
            self.audioreader.add_websocket_connection(self)
            self.audioreader.start()

        if data['type'] == 'start_speaker_transcript_processing':
            self.send_json({'type':'speaker metric computation started','message':"Computing Speaker Metric"})
            self.processorspeakermetric.add_websocket_connection(self)
            self.processorspeakermetric.start_speaker_metric_processing()
        if data['type'] == 'start_transcript_metric_processing':
            self.send_json({'type':'transcript metric computation started','message':"Computing Transcript Metric"})
            self.processorspeakermetric.add_websocket_connection(self)
            self.processorspeakermetric.start_transcript_metric_processing()    

        if data['type'] == 'heartbeat_from_posthoc_processing':
            auth_key = data.get('key', None)
            logging.info("Recieved Heartbeat from client with authkey {0}".format(auth_key))   




    def get_audio_file_path(self,sessionDeviceId):
        current_dir = Path(__file__).resolve().parent
        # Go up one level (parent)
        parent_dir = current_dir.parent
        # Go into sibling directory
        target_dir = parent_dir / "audio_processing" / "recordings"
        # Find file starting with prefix
        prefix = str(sessionDeviceId)
        files = list(target_dir.glob(f"{prefix}*"))

        if files:
            file_path = files[0]
            logging.info("Found:".format(file_path))
            return file_path
            # with open(file_path, "r") as f:
            #     content = f.read()
        else:
            logging.info("No file found")
            return None
    
    def read_bytes_from_wav(self,wav):
        wav.setpos(0)
        sdata = wav.readframes(wav.getnframes())
        data = np.frombuffer(sdata,dtype=np.dtype('int16'))
        return data.tobytes()

     # Changes the bit depth and encoding type.
    def reformat_data(self, in_data):
        if self.config.encoding == 'pcm_f32le':
            out_data = np.frombuffer(in_data, np.float32, -1)
            return (out_data * 32767.0).astype(np.int16, copy=False).tobytes()
        else:
            return in_data

    # Resampling leads to clicking in the output audio (scipy.signal.resample)
    def resample_data(self, in_data):
        if self.config.sample_rate != 16000:
            out_data = np.frombuffer(in_data, np.int16, -1)
            secs = len(out_data) / self.config.sample_rate
            samps = int(secs * 16000)
            return scipy.signal.resample(out_data, samps).astype(np.int16, copy=False).tobytes()
        else:
            return in_data

    # Reduces number of channels down to the desired amount.
    def reduce_channels(self, channels_wanted, in_data):
        if channels_wanted < self.config.channels:
            out_data = np.frombuffer(in_data, np.int16, -1)
            return out_data[channels_wanted::self.config.channels].tobytes()
        else:
            return in_data    

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)

    def send_close(self, message):
        self.send_json({'type': 'end', 'message': message})

    def signal_start(self):
        # WhisperX transcribes the whole file before emitting results, so the
        # buffer must retain the entire recording (2h cap ≈ 230MB PCM).
        buffer_seconds = 7200 if getattr(self, 'asr_choice', None) in ('whisperx', 'qwen3') else None
        self.audio_buffer = AudioBuffer(self.config, max_seconds=buffer_seconds)
        self.asr_audio_queue = Queue()
        self.asr_transcript_queue = Queue()
        # Per-run ASR choice from the trigger UI (falls back to config.ini).
        # Whisper consumes the same PCM queue and runs fully offline; import
        # lazily so the Google path never needs faster-whisper installed.
        if getattr(self, 'asr_choice', None) == 'qwen3':
            from asr_connectors.qwen3_asr import Qwen3ASR
            self.asr = Qwen3ASR(self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data, self.interval,
                                audio_file=self.audio_file,
                                diarize=(getattr(self, 'diarizer_choice', None) == 'pyannote'))
        elif getattr(self, 'asr_choice', None) == 'whisperx':
            from asr_connectors.whisperx_asr import WhisperXASR
            self.asr = WhisperXASR(self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data, self.interval,
                                   audio_file=self.audio_file, model_size=cf.whisper_model_size(),
                                   diarize=(getattr(self, 'diarizer_choice', None) == 'pyannote'))
        elif getattr(self, 'asr_choice', None) == 'whisper':
            from asr_connectors.whisper_asr import WhisperASR
            self.asr = WhisperASR(self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data, self.interval)
        else:
            self.asr = GoogleASR(self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data,self.interval,STOP_SIGNAL)
        self.asr.start()
        self.processor = AudioProcessorPosthoc(self.audio_buffer, self.asr_transcript_queue, diarization_model, semantic_model, self.config, scorer=getattr(self, 'scorer_choice', None))
        self.processor.start()
        self.audioreader = AudioStreamReader(self.audio_buffer, self.asr_audio_queue, self.audio_file, self.queue_put_timeout,self.config,STOP_SIGNAL,running_audio_processes)
        

    def signal_end(self):
        if self.asr:
            self.asr.stop()
        if self.processor:
            self.processor.stop()
        if self.audioreader:
            self.audioreader.stop()
        if self.processorspeakermetric:
            self.processorspeakermetric.stop()

        if self.config:
            cm.remove(self, self.config.session_key, self.config.auth_key)

       
        else:
            cm.remove(self, None, None)
        logging.info('Closing client connection...')
        self.transport.loseConnection()

        # Begin Post Processing
        if cf.record_reduced():
            self.redu_recorder.close()
       
        if cf.record_original():
            self.orig_recorder.close()
            

if __name__ == '__main__':
    cf.initialize()
    # Initialize Logger
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_file = logging.FileHandler(os.path.join(dir_path, 'audio_posthoc_processing_service.log'))
    log_file.setFormatter(log_format)
    logger.addHandler(log_file)
    log_console = logging.StreamHandler()
    log_console.setFormatter(log_format)
    logger.addHandler(log_console)


    # Run Server
    logging.info('Starting Audio Posthoc Processing Service...')
    features_detector.initialize()
    keyword_detector.initialize(cf.keyword_model_limit())

    poll_connections = task.LoopingCall(cm.check_connections)
    poll_connections.start(10.0)
    auth_connections = task.LoopingCall(cm.check_connection_authentication)
    auth_connections.start(5.0)
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(int(os.environ.get("DC_AUDIO_POSTHOC_WS_PORT", 9005)), factory)
    logging.info('Audio Posthoc Processing Service started.')
    reactor.run()
    logging.info('Audio Posthoc Processing Service ended.')