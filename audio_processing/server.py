import os
import json
import time
import glob
import queue
import shutil
import logging
import callbacks
import threading
import weakref
import wave
import scipy.signal
import config as cf
import numpy as np
import moviepy.editor as mp
from recorder import WaveRecorder
from recorder import VidRecorder
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager
from audio_buffer import AudioBuffer
from processor import AudioProcessor
from datetime import datetime
from redis_helper import RedisSessions
from twisted.python import log
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from asr_connectors.google_asr_connector import GoogleASR
from features_detector import features_detector
from keyword_detector import keyword_detector
from speaker_tagging import speaker_tagging

cm = ConnectionManager()

class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = None
        self.running = False
        self.audio_buffer = None
        self.asr_audio_queue = None
        self.asr_transcript_queue = None
        self.asr = None
        self.processor = None
        self.last_message = time.time()
        self.end_signaled = False
        self.interval = 10
        self.awaitingSpeakers = True
        self.speakers = None
        self.currSpeaker = None
        self.currAlias = None
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

    def onClose(self, *args, **kwargs):
        self.signal_end()

    def process_json(self, data):
        if not 'type' in data:
            logging.warning('Message does not contain "type".')
            return
        if data['type'] == 'speaker':
            if data['id'] == "done":
                self.awaitingSpeakers = False
                for speaker in data['speakers']:
                    self.speakers[speaker["id"]]["alias"] = speaker["alias"]
                self.processor.setSpeakerFingerprints(self.speakers)
                logging.info("Done awaiting all speakers info")
            else:
                self.currSpeaker = data['id']
                self.currAlias = data['alias']
                logging.info("preparing for speaker {}'s fingerprint".format(self.currSpeaker))
        if data['type'] == 'start':
            valid, result = ProcessingConfig.from_json(data)
            if not valid:
                self.send_json({'type': 'error', 'message': result})
                self.signal_end()
            else:
                self.config = result
                cm.associate_keys(self, self.config.session_key, self.config.auth_key)
                self.stream_data = data['streamdata']
                if(data['numSpeakers'] != 0):
                    self.speakers = dict()

                if self.stream_data == 'audio':
                    if cf.record_original():
                        filename = os.path.join(cf.recordings_folder(), "{0} ({1})_orig".format(self.config.auth_key, str(time.ctime())))
                        self.orig_recorder = WaveRecorder(filename, self.config.sample_rate, self.config.depth, self.config.channels)
                    if cf.record_reduced():
                        filename = os.path.join(cf.recordings_folder(), "{0} ({1})_redu".format(self.config.auth_key, str(time.ctime())))
                        self.redu_recorder = WaveRecorder(filename, 16000, 2, 1)
                elif self.stream_data == 'video':
                    self.video_count = 1
                    self.filename = os.path.join(cf.video_recordings_folder(), "{0}_{1}_{2}_({3})_orig".format(self.config.auth_key,self.config.sessionId,self.config.deviceId, str(time.ctime())))
                    self.orig_vid_recorder = VidRecorder(self.filename,16000, 2, 1)
                self.signal_start()
                self.send_json({'type':'start'})
                logging.info('Audio process connected')
                callbacks.post_connect(self.config.auth_key)

    def process_binary(self, data):
        if self.running and not self.awaitingSpeakers:
            if self.stream_data == 'audio':
                if cf.record_original():
                    # Save audio data.
                    self.orig_recorder.write(data)
                # Convert all audio to pcm_i16le
                data = self.reformat_data(data)
                data = self.resample_data(data)
                self.audio_buffer.append(data)
                asr_data = self.reduce_channels(1, data)
                self.asr_audio_queue.put(asr_data)
                # Save audio data.
                if cf.record_reduced():
                    self.redu_recorder.write(asr_data)
            elif self.stream_data == 'video':
                self.orig_vid_recorder.write(data)

                temp_aud_file = os.path.join(cf.video_recordings_folder(), "{0} ({1})_tempvid".format(self.config.auth_key, str(time.ctime())))
                vidclip = mp.VideoFileClip(self.filename+'.webm')
                subclips = vidclip.subclip((self.video_count-1)*self.interval,self.video_count*self.interval)
                subclips.audio.write_audiofile(temp_aud_file+'.wav',fps=16000,bitrate='50k') #nbytes=2,codec='pcm_s16le',

                wavObj = wave.open(temp_aud_file+'.wav')
                self.audio_buffer.append(self.read_bytes_from_wav(wavObj))
                audiobyte = self.reduce_wav_channel(1,wavObj)
                self.asr_audio_queue.put(audiobyte)

                if os.path.isfile(temp_aud_file+'.wav'):
                    os.remove(temp_aud_file+'.wav')

                self.video_count = self.video_count + 1
                logging.info('video binary recieved')
        elif self.running and self.awaitingSpeakers:
            if self.currSpeaker:
                new_data = self.reformat_data(data)
                self.speakers[self.currSpeaker] = {"alias": self.currAlias, "data": new_data}
                logging.info("storing speaker {}'s fingerprint with alias {}".format(self.currSpeaker, self.currAlias))
                self.currSpeaker = None
                self.currAlias = None
        else:
            self.send_json({'type': 'error', 'message': 'Binary audio data sent before start message.'})

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)

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

    def read_bytes_from_wav(self,wav):
        wav.setpos(0)
        sdata = wav.readframes(wav.getnframes())
        data = np.frombuffer(sdata,dtype=np.dtype('int16'))
        return data.tobytes()

    def reduce_wav_channel(self,channels_wanted,wav):
        if channels_wanted < self.config.channels:
            nch = wav.getnchannels()
            wav.setpos(0)
            sdata = wav.readframes(wav.getnframes())
            data = np.frombuffer(sdata,dtype=np.dtype('int16'))
            ch_data = data[0::nch]
            return ch_data.tobytes()
        else:
            self.read_bytes_from_wav(wav)



    def signal_start(self):
        self.audio_buffer = AudioBuffer(self.config)
        self.asr_audio_queue = queue.Queue()
        self.asr_transcript_queue = queue.Queue()
        self.asr = GoogleASR(self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data,self.interval)
        self.asr.start()
        self.processor = AudioProcessor(self.audio_buffer, self.asr_transcript_queue, self.config)
        self.processor.start()
        self.running = True

    def send_close(self, message):
        self.send_json({'type': 'end', 'message': message})

    def signal_end(self):
        if self.end_signaled:
            return
        self.end_signaled = True
        if self.asr:
            self.asr.stop()
        if self.processor:
            self.processor.stop()

        if self.config:
            callbacks.post_disconnect(self.config.auth_key)
            cm.remove(self, self.config.session_key, self.config.auth_key)
        else:
            cm.remove(self, None, None)
        logging.info('Closing client connection...')
        self.transport.loseConnection()

        # Begin Post Processing
        if cf.record_reduced():
            self.redu_recorder.close()
        # if self.stream_data == 'video':
        #     self.orig_vid_recorder.close()
        if cf.record_original():
            self.orig_recorder.close()
            '''
            if self.config.tag:
                logging.info('Performing speaker tagging...')
                tagging_results = speaker_tagging.speaker_tagging(self.orig_recorder.wav_filename)
                taggings_posted = callbacks.post_tagging(self.config.auth_key, tagging_results)

                if taggings_posted:
                    logging.info('Processing results posted successfully for tagging {0} '.format(self.config.auth_key))
                else:
                    logging.info('Processing results FAILED to post for {0} '.format(self.config.auth_key))
            '''

if __name__ == '__main__':
    cf.initialize()

    # Initialize Logger
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_format = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    log_file = logging.FileHandler(os.path.join(dir_path, 'audio_processing_service.log'))
    log_file.setFormatter(log_format)
    logger.addHandler(log_file)
    log_console = logging.StreamHandler()
    log_console.setFormatter(log_format)
    logger.addHandler(log_console)

    # Run Server
    logging.info('Starting Audio Processing Service...')
    features_detector.initialize()
    keyword_detector.initialize(cf.keyword_model_limit())
    poll_connections = task.LoopingCall(cm.check_connections)
    poll_connections.start(10.0)
    auth_connections = task.LoopingCall(cm.check_connection_authentication)
    auth_connections.start(5.0)
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(9000, factory)
    logging.info('Audio Processing Service started.')
    reactor.run()
    logging.info('Audio Processing Service ended.')
