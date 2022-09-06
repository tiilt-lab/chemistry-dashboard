from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
from google.api_core import exceptions
from google.cloud import speech as speechV1
import os
import time
import math
import logging
import threading

# For converting nano seconds to seconds.
NANO = 1000000000

# Path for google asr credentials.
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/var/lib/chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json'

class GoogleASR():
    STREAM_LIMIT = 55.0
    SAMPLE_RATE = 16000
    SAMPLE_RATE_WAV = 44100
    DEPTH = 2

    def __init__(self, audio_queue, transcript_queue, config,mediatype):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.running = False
        self.audio_time = 0.0
        self.media_type = mediatype

    def start(self):
        self.running = True
        if self.media_type == 'audio':
            self.asr_thread = threading.Thread(target=self.processing, name="google-cloud-speech")
        elif self.media_type == 'video':
            self.asr_thread = threading.Thread(target=self.processing_wav_audio, name="google-cloud-speech-wav-audio")
        self.asr_thread.daemon = True
        self.asr_thread.start()

    def stop(self):
        self.running = False

    def generator(self):
        generator_time = 0
        while self.running and generator_time < GoogleASR.STREAM_LIMIT:
            chunk = self.audio_queue.get()
            data = [chunk]
            if chunk is None:
                return
            while not self.audio_queue.empty():
                chunk = self.audio_queue.get(block=False)
                if chunk is None:
                    return
                data.append(chunk)
            for chunk in data:
                generator_time += (len(chunk) / GoogleASR.DEPTH) / GoogleASR.SAMPLE_RATE
            # logging.info('yielded data {0}'.format(b''.join(data)))
            yield b''.join(data)
        self.audio_time += generator_time
        

    def process_responses(self, responses, audio_start_time):
        for response in responses:
            if not response.results:
                continue
            logging.info('Response is:  {}'.format(response))
            result = response.results[0]
            if not result.alternatives:
                continue
            if result.is_final and len(result.alternatives[0].words) > 0:
                logging.info('i was here prcosess_resp 3 {}'.format(result.alternatives[0].words))
                end_time = result.result_end_time
                end_time.seconds, end_time.nanos = self.adjust_time(end_time.seconds, end_time.nanos, audio_start_time)
                for word in result.alternatives[0].words:
                    start = word.start_time
                    end = word.end_time
                    start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
                    end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)
                self.transcript_queue.put(result)

    def process_wav_responses(self, response, audio_start_time):
        #for response in responses:
        #logging.info('iteration count {0}'.format(count))
        if not response.results:
            logging.info('i was here prcosess_resp {}'.format(response.results))
            return
        
        result = response.results[0] if response.results[0].alternatives[0].confidence > response.results[1].alternatives[0].confidence else response.results[1]
        if not result.alternatives:
            logging.info('i was here prcosess_resp 2 {}'.format(result.alternatives))
            return
        
        if  len(result.alternatives[0].words) > 0:
            logging.info('i was here prcosess_resp 3 {}'.format(result.alternatives[0].words))
            # end_time = result.result_end_time
            # end_time.seconds, end_time.nanos = self.adjust_time(end_time.seconds, end_time.nanos, audio_start_time)
            # logging.info('result endtime and endtime sec {0} {1} {2}'.format(end_time,end_time.seconds,end_time.nanos))
            for word in result.alternatives[0].words:
                start = word.start_time
                end = word.end_time
                start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
                end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)
            self.transcript_queue.put(result)

    def adjust_time(self, seconds, nanos, offset):
        adjusted_time = seconds + (nanos / NANO) + offset
        adjusted_nanos, adjusted_seconds = math.modf(adjusted_time)
        adjusted_nanos *= NANO
        return int(adjusted_seconds), int(adjusted_nanos)

    def processing(self):
        logging.info('Google ASR thread started for {0}.'.format(self.config.auth_key))
        language_code = 'en-US'

        client = speech.SpeechClient()
        recognition_config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=GoogleASR.SAMPLE_RATE,
            language_code=language_code,
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
            model='video')
        streaming_config = types.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=False)

        # This loop runs to get around the (currently) 65-second time limit for streaming audio recognition.
        # Each generator closes after 55 seconds of audio, allowing for a new stream to open.
        # NOTE: Audio can still clip on stream change overs.  Might need VAD in the future to avoid clipping speech.
        while self.running:
            try:
                logging.info('i was here 1')
                audio_generator = self.generator()
                logging.info('i was here 2 {0}'.format(audio_generator))
                requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
                responses = client.streaming_recognize(streaming_config, requests)
                self.process_responses(responses, self.audio_time)
            except exceptions.InvalidArgument as e:
                logging.warning('Invalid args for Google ASR Connector for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
            except exceptions.OutOfRange as e:
                # Request dies if either maximum time limit or there is a long duration wihout audio
                if 'maximum allowed stream duration' not in e.message and 'being streamed too' not in e.message and 'Long duration elapsed without audio' not in e.message:
                    logging.warning('Stream max length exceeded for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
                if 'being streamed too fast' in e.message:
                    logging.warning('Audio data is being streamed to fast for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
            except Exception as e:
                if e.message == 'DNS resolution failed':
                    logging.critical('Google ASR failed to reach DNS server. Please verify that the default network route has an internet connection.  Shutting down...')
                    break
                logging.warning('Error in Google ASR Connector for client {0}: {1}'.format(self.config.auth_key, e.message))
        logging.info('Google ASR thread stopped for {0}.'.format(self.config.auth_key))
        self.transcript_queue.put(None)

    def processing_wav_audio(self):
        logging.info('Google WAV ASR thread started for {0}.'.format(self.config.auth_key))
        language_code = 'en-US'

        client = speech.SpeechClient()
        recognition_config = types.RecognitionConfig(
            sample_rate_hertz=GoogleASR.SAMPLE_RATE_WAV,
            language_code=language_code,
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
            audio_channel_count = 2,
            enable_separate_recognition_per_channel = True,
            model='video')
        
        # This loop runs to get around the (currently) 65-second time limit for streaming audio recognition.
        # Each generator closes after 55 seconds of audio, allowing for a new stream to open.
        # NOTE: Audio can still clip on stream change overs.  Might need VAD in the future to avoid clipping speech.
        while self.running:
            try:
                if not self.audio_queue.empty():
                    audio_wav = types.RecognitionAudio(content=self.audio_queue.get()) 
                    responses = client.recognize(config = recognition_config, audio=audio_wav)
                    self.process_wav_responses(responses, self.audio_time)
            except exceptions.InvalidArgument as e:
                logging.warning('Invalid args for Google ASR Connector for client {0}. Attempting to restart connection... {1}'.format(self.config.auth_key,e))
            except exceptions.OutOfRange as e:
                # Request dies if either maximum time limit or there is a long duration wihout audio
                if 'maximum allowed stream duration' not in e.message and 'being streamed too' not in e.message and 'Long duration elapsed without audio' not in e.message:
                    logging.warning('Stream max length exceeded for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
                if 'being streamed too fast' in e.message:
                    logging.warning('Audio data is being streamed to fast for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
            except Exception as e:
                if hasattr(e, 'message') and e.message == 'DNS resolution failed':
                    logging.critical('Google ASR failed to reach DNS server. Please verify that the default network route has an internet connection.  Shutting down...')
                    break
                logging.warning('Error in Google ASR Connector for client {0}: {1}'.format(self.config.auth_key, e))
        logging.info('Google ASR thread stopped for {0}.'.format(self.config.auth_key))
        self.transcript_queue.put(None)

