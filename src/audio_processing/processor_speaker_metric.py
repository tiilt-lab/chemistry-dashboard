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
from features_detector.features_detector import detect_LIWC_Indices
from queue import Full
import config as cf
import json

class SpeakerMetricProcessor:
    def __init__(self, sessionid, session_device_id, transcripts, semantic_model, config,running_audio_processes, scorer=None):
        self.sessionid = sessionid
        self.session_device_id = session_device_id
        self.transcripts = transcripts
        # E&T scoring backend for the re-computation (liwc | open | llm);
        # None keeps the default composite LIWC indices.
        self.scorer = scorer
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

    def start_speaker_metric_processing(self):
        self.processing_thread = threading.Thread(target=self.process_speaker_metrics,name="speaker_metric_processing")
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def start_transcript_metric_processing(self):
        self.processing_thread = threading.Thread(target=self.process_transcript_metrics,name="transcript_metric_processing")
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


    def process_speaker_metrics(self):
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

    def process_transcript_metrics(self):
        try:
            # Re-score every utterance with the chosen E&T backend and persist
            # the five feature values back onto the transcript rows. (The
            # original implementation computed and only logged the scores.)
            FEATURE_KEYS = ('emotional_tone_value', 'analytic_thinking_value',
                            'clout_value', 'authenticity_value', 'certainty_value')
            # Composite-LIWC balance indices are 0..1; the DB convention (live
            # pipeline and the other scorers) is 0..100.
            BALANCE_KEYS = ('emotional_tone_value', 'clout_value', 'certainty_value')

            scoring_fn = None
            if self.scorer in ('open', 'llm'):
                from features_detector import scorer_factory
                scoring_fn = scorer_factory.get_scorer(self.scorer).detect_features

            updates = []
            for transcriptObj in self.transcripts:
                # id,start_time, speaker_id, speaker_tag,transcript
                if scoring_fn is not None:
                    summary = scoring_fn(transcriptObj['transcript'])
                else:
                    summary = detect_LIWC_Indices(transcriptObj['transcript'])
                    summary = dict(summary)
                    for k in BALANCE_KEYS:
                        summary[k] = round(100.0 * summary[k], 2)
                updates.append({
                    'id': transcriptObj['id'],
                    'features': {k: summary.get(k, 0) for k in FEATURE_KEYS},
                })

            posted = callbacks.post_transcript_features(self.config.auth_key, updates)
            logging.info('transcript metric recompute (%s): %d utterances, persisted=%s',
                         self.scorer or 'liwc', len(updates), posted)
        except Exception as e:
            error_str = traceback.format_exc()
            logging.info('exception occured while computing transcript metrics  : {0}'.format(error_str))
        finally:
            try:
                self.running_audio_processes.pop(self.config.auth_key,None)
                logging.info('transcript metric computation thread stopped for {0}.'.format(self.config.auth_key))
                self.send_json({'type': 'process_completed', 'message': "Transcript Metric Computation Completed"})  
            except Full:
                pass        

       
