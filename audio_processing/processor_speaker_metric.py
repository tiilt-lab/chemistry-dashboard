"""_summary_

Returns:
    _description_
"""

import time
import os
import logging
import threading
import callbacks
import traceback
from speaker_metrics import speaker_metrics
from queue import Full
import config as cf
import json

class SpeakerMetricProcessor:
    def __init__(self, sessionid, session_device_id, transcripts, semantic_model, config,running_audio_processes):
        self.sessionid = sessionid
        self.session_device_id = session_device_id
        self.transcripts = transcripts
        self.running_audio_processes = running_audio_processes
        self.speakers = None
        self.config = config
        self.running = False
        self.running_processes = 0
        self.fingerprints = None
        self.cohesion_window = 20

        self.semantic_model = semantic_model
        logging.info("Start metrics process")
        self.speaker_metrics_process = speaker_metrics.SpeakerProcessor(
            config, self.semantic_model,usedby='speaker metric processor')

        cf.initialize()

    def start(self):
        self.processing_thread = threading.Thread(target=self.process,name="audio_stream_reader")
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop(self):
        self.running = False

    def add_websocket_connection(self,web_socket):
        self.web_socket_connection = web_socket

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.web_socket_connection.sendMessage(payload, isBinary = False)

    def setSpeakerFingerprints(self, fingerprints):
        self.fingerprints = fingerprints
        logging.info("Set Speakers")
        self.speaker_metrics_process.setSpeakers(self.fingerprints)


    def process(self):
        try:
            for transcriptObj in self.transcripts:
                # id,start_time, speaker_id, speaker_tag,transcript
                self.speaker_metrics_process.process_transcript(
                    {
                        'source': self.config.auth_key,
                        'transcript_id': transcriptObj['id'],
                        'start_time': transcriptObj['start_time'],
                        'transcript': transcriptObj['transcript'],
                        'speaker_tag': transcriptObj['speaker_tag'],
                        'speaker_id': transcriptObj['speaker_id']
                    },action="speaker metric recomputation")
                
                # compute_particpation_score(transcriptObj['speaker_id'],transcriptObj['start_time'],transcriptObj['transcript'])
              
        except Exception as e:
            error_str = traceback.format_exc()
            logging.info('exception occured while computing speaker metrics  : {0}'.format(error_str))
        finally:
            try:
                self.running_audio_processes.pop(self.config.auth_key,None)
                logging.info('Speaker metric computation thread stopped for {0}.'.format(self.config.auth_key))
                self.send_json({'type': 'process_completed', 'message': "Speaker Metric Computation Completed"})  
            except Full:
                pass

       
