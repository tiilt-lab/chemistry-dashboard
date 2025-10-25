from email.mime import audio
from http.client import responses
from google.cloud import speech_v1p1beta1 as speech
from google.cloud.speech_v1p1beta1 import enums
from google.cloud.speech_v1p1beta1 import types
from google.api_core import exceptions
from google.cloud import speech as speechV1
from queue import Empty
import os
import time
import math
import logging
import threading
import config as cf
import numpy as np

# For converting nano seconds to seconds.
NANO = 1000000000

# Path for google asr credentials.
cf.initialize()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cf.root_dir()+'chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json'
os.environ['GRPC_DNS_RESOLVER'] = 'native'

class GoogleASR():
    STREAM_LIMIT = 55.0
    SAMPLE_RATE = 16000
    DEPTH = 2

    def __init__(self, audio_queue, transcript_queue, config,mediatype,interval):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.running = False
        self.audio_time = 0.0
        self.audio_interval = interval
        self.audio_file_duration = 0
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
            yield b''.join(data)
        self.audio_time += generator_time
        

    def process_responses(self, responses, audio_start_time):
        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            if result.is_final and len(result.alternatives[0].words) > 0:
                # are these tme calculations really needed? does not appear to be used anywhere
                end_time = result.result_end_time
                end_time.seconds, end_time.nanos = self.adjust_time(end_time.seconds, end_time.nanos, audio_start_time)
                # are these tme calculations really needed? does not appear to be used anywhere
                for word in result.alternatives[0].words:
                    start = word.start_time
                    end = word.end_time
                    start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
                    end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)
                self.transcript_queue.put(result)

    def process_wav_responses(self, response, audio_start_time):
        for result in response.results:
            if not result.alternatives:
                return
            
            if  len(result.alternatives[0].words) > 0:
                for word in result.alternatives[0].words:
                    # are these tme calculations really needed? does not appear to be used anywhere
                    start = word.start_time
                    end = word.end_time
                    start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
                    end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)
                self.transcript_queue.put(result)

    def adjust_time(self, seconds, nanos, offset):
        adjusted_time = seconds + (nanos / NANO) + offset
        adjusted_nanos, adjusted_seconds = math.modf(adjusted_time)
        adjusted_nanos *= NANO
        adjusted_seconds += self.audio_file_duration
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
            config= recognition_config,
            interim_results=False)

        # This loop runs to get around the (currently) 65-second time limit for streaming audio recognition.
        # Each generator closes after 55 seconds of audio, allowing for a new stream to open.
        # NOTE: Audio can still clip on stream change overs.  Might need VAD in the future to avoid clipping speech.
        while self.running:
            try:
                audio_generator = self.generator()
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
                if hasattr(e, 'message') and e.message == 'DNS resolution failed':
                    logging.critical('Google ASR failed to reach DNS server. Please verify that the default network route has an internet connection.  Shutting down...')
                    break
                logging.warning('Error in Google ASR Connector for client {0}: {1}'.format(self.config.auth_key, e))
        logging.info('Google ASR thread stopped for {0}.'.format(self.config.auth_key))
        self.transcript_queue.put(None)

    def processing_wav_audio(self):
        logging.info('Google WAV ASR thread started for {0}.'.format(self.config.auth_key))
        language_code = 'en-US'

        client = speech.SpeechClient()
        recognition_config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=GoogleASR.SAMPLE_RATE,
            language_code=language_code,
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
            audio_channel_count = 1,
            #enable_separate_recognition_per_channel = True,
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
                    self.audio_file_duration = self.audio_file_duration + self.audio_interval
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
        
# class GoogleASR():
#     STREAM_LIMIT = 55.0
#     SAMPLE_RATE = 16000
#     DEPTH = 2

#     def __init__(self, audio_queue, transcript_queue, config,mediatype,interval):
#         self.audio_queue = audio_queue
#         self.transcript_queue = transcript_queue
#         self.config = config
#         self.running = False
#         self.audio_time = 0.0
#         self.audio_interval = interval
#         self.audio_file_duration = 0
#         self.media_type = mediatype

#     def start(self):
#         self.running = True
#         if self.media_type == 'audio':
#             self.asr_thread = threading.Thread(target=self.processing, name="google-cloud-speech")
#         elif self.media_type == 'video':
#             self.asr_thread = threading.Thread(target=self.processing_wav_audio, name="google-cloud-speech-wav-audio")
#         self.asr_thread.daemon = True
#         self.asr_thread.start()

#     def stop(self):
#         self.running = False

#     def generator(self):
#         BYTES_PER_SAMPLE = GoogleASR.DEPTH          # e.g., 2 for 16-bit
#         SR = GoogleASR.SAMPLE_RATE                  # e.g., 16000
#         CH = getattr(GoogleASR, "CHANNELS", 1)      # default mono if missing
#         STREAM_LIMIT = GoogleASR.STREAM_LIMIT       # seconds
#         TARGET_BATCH_SEC = 0.20                     # ~200 ms per yield (tune to taste)

#         def secs_from_bytes(nbytes: int) -> float:
#             return nbytes / (SR * BYTES_PER_SAMPLE * CH)

#         elapsed = 0.0
#         try:
#             while self.running and elapsed < STREAM_LIMIT:
#                 # Block briefly for the first chunk to avoid spin
#                 try:
#                     chunk = self.audio_queue.get(timeout=0.25)
#                 except Empty:
#                     continue

#                 if chunk is None:
#                     break  # graceful shutdown

#                 batch = [chunk]
#                 total_bytes = len(chunk)
#                 stop_after_yield = False

#                 # Drain quickly up to TARGET_BATCH_SEC without racing on .empty()
#                 target_bytes = int(TARGET_BATCH_SEC * SR * BYTES_PER_SAMPLE * CH)
#                 while total_bytes < target_bytes:
#                     try:
#                         nxt = self.audio_queue.get_nowait()
#                     except Empty:
#                         break
#                     if nxt is None:
#                         stop_after_yield = True  # flush, then exit
#                         break
#                     batch.append(nxt)
#                     total_bytes += len(nxt)

#                 secs = secs_from_bytes(total_bytes)

#                 # Optional: cap at STREAM_LIMIT boundary (simple: stop after this yield)
#                 if elapsed + secs > STREAM_LIMIT:
#                     # You could split the last chunk here if you need exact limits.
#                     pass

#                 elapsed += secs
#                 yield b"".join(batch)

#                 if stop_after_yield:
#                     break
#         finally:
#             # Ensure we always account for time we streamed, even on early returns
#             self.audio_time += elapsed        

#     def process_responses(self, responses, audio_start_time):
#         for response in responses:
#             if not response.results:
#                 continue
#             result = response.results[0]
#             if not result.alternatives:
#                 continue
#             if result.is_final and len(result.alternatives[0].words) > 0:
#                 # are these tme calculations really needed? does not appear to be used anywhere
#                 end_time = result.result_end_time
#                 end_time.seconds, end_time.nanos = self.adjust_time(end_time.seconds, end_time.nanos, audio_start_time)
#                 # are these tme calculations really needed? does not appear to be used anywhere
#                 for word in result.alternatives[0].words:
#                     start = word.start_time
#                     end = word.end_time
#                     start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
#                     end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)  
#                 self.transcript_queue.put(result)

#     def process_wav_responses(self, response, audio_start_time):
#         for result in response.results:
#             if not result.alternatives:
#                 return
            
#             if  len(result.alternatives[0].words) > 0:
#                 for word in result.alternatives[0].words:
#                     # are these tme calculations really needed? does not appear to be used anywhere
#                     start = word.start_time
#                     end = word.end_time
#                     start.seconds, start.nanos = self.adjust_time(start.seconds, start.nanos, audio_start_time)
#                     end.seconds, end.nanos = self.adjust_time(end.seconds, end.nanos, audio_start_time)
#                 self.transcript_queue.put(result)

#     def adjust_time(self, seconds, nanos, offset):
#         adjusted_time = seconds + (nanos / NANO) + offset
#         adjusted_nanos, adjusted_seconds = math.modf(adjusted_time)
#         adjusted_nanos *= NANO
#         adjusted_seconds += self.audio_file_duration
#         return int(adjusted_seconds), int(adjusted_nanos)

#     def processing(self):
#         logging.info('Google ASR thread started for {0}.'.format(self.config.auth_key))
#         language_code = 'en-US'
#         client = speech.SpeechClient()
#         recognition_config = types.RecognitionConfig(
#             encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
#             sample_rate_hertz=GoogleASR.SAMPLE_RATE,
#             language_code=language_code,
#             enable_word_time_offsets=True,
#             enable_automatic_punctuation=True,
#             model='video')
#         streaming_config = types.StreamingRecognitionConfig(
#             config= recognition_config,
#             interim_results=False)
#         # This loop runs to get around the (currently) 65-second time limit for streaming audio recognition.
#         # Each generator closes after 55 seconds of audio, allowing for a new stream to open.
#         # NOTE: Audio can still clip on stream change overs.  Might need VAD in the future to avoid clipping speech.
#         logging.info('self.running {0}'.format(self.running))
#         while self.running:
#             try:
#                 audio_generator = self.generator()
#                 requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
#                 responses = client.streaming_recognize(streaming_config, requests)
#                 self.process_responses(responses, self.audio_time)
#             except exceptions.InvalidArgument as e:
#                 logging.warning('Invalid args for Google ASR Connector for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
#             except exceptions.OutOfRange as e:
#                 # Request dies if either maximum time limit or there is a long duration wihout audio
#                 if 'maximum allowed stream duration' not in e.message and 'being streamed too' not in e.message and 'Long duration elapsed without audio' not in e.message:
#                     logging.warning('Stream max length exceeded for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
#                 if 'being streamed too fast' in e.message:
#                     logging.warning('Audio data is being streamed to fast for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
#             except Exception as e:
#                 if hasattr(e, 'message') and e.message == 'DNS resolution failed':
#                     logging.critical('Google ASR failed to reach DNS server. Please verify that the default network route has an internet connection.  Shutting down...')
#                     break
#                 logging.warning('Error in Google ASR Connector for client {0}: {1}'.format(self.config.auth_key, e))
#         logging.info('Google ASR thread stopped for {0}.'.format(self.config.auth_key))
#         self.transcript_queue.put(None)

#     def processing_wav_audio(self):
#         logging.info('Google WAV ASR thread started for {0}.'.format(self.config.auth_key))
#         language_code = 'en-US'

#         client = speech.SpeechClient()
#         recognition_config = types.RecognitionConfig(
#             encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
#             sample_rate_hertz=GoogleASR.SAMPLE_RATE,
#             language_code=language_code,
#             enable_word_time_offsets=True,
#             enable_automatic_punctuation=True,
#             audio_channel_count = 1,
#             #enable_separate_recognition_per_channel = True,
#             model='video')
        
#         # This loop runs to get around the (currently) 65-second time limit for streaming audio recognition.
#         # Each generator closes after 55 seconds of audio, allowing for a new stream to open.
#         # NOTE: Audio can still clip on stream change overs.  Might need VAD in the future to avoid clipping speech.
#         while self.running:
#             try:
#                 if not self.audio_queue.empty():
#                     audio_wav = types.RecognitionAudio(content=self.audio_queue.get()) 
#                     responses = client.recognize(config = recognition_config, audio=audio_wav)
#                     self.process_wav_responses(responses, self.audio_time)
#                     self.audio_file_duration = self.audio_file_duration + self.audio_interval
#             except exceptions.InvalidArgument as e:
#                 logging.warning('Invalid args for Google ASR Connector for client {0}. Attempting to restart connection... {1}'.format(self.config.auth_key,e))
#             except exceptions.OutOfRange as e:
#                 # Request dies if either maximum time limit or there is a long duration wihout audio
#                 if 'maximum allowed stream duration' not in e.message and 'being streamed too' not in e.message and 'Long duration elapsed without audio' not in e.message:
#                     logging.warning('Stream max length exceeded for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
#                 if 'being streamed too fast' in e.message:
#                     logging.warning('Audio data is being streamed to fast for client {0}. Attempting to restart connection...'.format(self.config.auth_key))
#             except Exception as e:
#                 if hasattr(e, 'message') and e.message == 'DNS resolution failed':
#                     logging.critical('Google ASR failed to reach DNS server. Please verify that the default network route has an internet connection.  Shutting down...')
#                     break
#                 logging.warning('Error in Google ASR Connector for client {0}: {1}'.format(self.config.auth_key, e))
#         logging.info('Google ASR thread stopped for {0}.'.format(self.config.auth_key))
#         self.transcript_queue.put(None)

