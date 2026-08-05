"""
Google Cloud Speech-to-Text V2 API Connector with Chirp 2 model.

Uses streaming recognition with built-in VAD and word-level timestamps.
Outputs V1-compatible format for processor.py compatibility.

CRITICAL: This uses Chirp 2 (not Chirp 3) because Chirp 3 does NOT support
word-level timestamps, which are required by processor.py for audio extraction.
"""
import os
import json
import time
import math
import logging
import threading
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
import config as cf

# For converting nanoseconds to seconds
NANO = 1000000000

# V2 API requires regional endpoint
REGION = "us-central1"
API_ENDPOINT = f"{REGION}-speech.googleapis.com"

cf.initialize()
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cf.root_dir() + 'chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json'
os.environ['GRPC_DNS_RESOLVER'] = 'native'


# V1-compatible wrapper classes for processor.py
class WordTiming:
    """Mimics V1 word timing format (seconds/nanos structure)."""
    def __init__(self, seconds, nanos):
        self.seconds = seconds
        self.nanos = nanos


class Word:
    """
    Mimics V1 word format.

    V2 API uses start_offset/end_offset (datetime.timedelta objects).
    V1 API uses start_time/end_time (with .seconds/.nanos).
    This class converts V2 format to V1 format for processor.py compatibility.
    """
    def __init__(self, word_text, start_offset, end_offset):
        self.word = word_text
        # V2 returns timedelta objects - convert to seconds/nanos
        start_total = start_offset.total_seconds()
        end_total = end_offset.total_seconds()
        self.start_time = WordTiming(
            int(start_total),
            int((start_total % 1) * 1000000000)
        )
        self.end_time = WordTiming(
            int(end_total),
            int((end_total % 1) * 1000000000)
        )


class Alternative:
    """Mimics V1 alternative format."""
    def __init__(self, transcript, words):
        self.transcript = transcript
        self.words = words


class TranscriptResult:
    """Mimics V1 StreamingRecognitionResult format for processor.py."""
    def __init__(self, transcript, words):
        self.alternatives = [Alternative(transcript, words)]
        self.is_final = True


class GoogleChirp2ASR:
    """
    Google Cloud Speech-to-Text V2 API connector with Chirp 2 model.

    Features:
    - Word-level timestamps (REQUIRED by processor.py)
    - Built-in VAD (eliminates audio clipping on stream changeovers)
    - Built-in denoising (better for noisy classrooms)
    - Improved accuracy over V1 'video' model

    Why Chirp 2 (not Chirp 3):
    - Chirp 3 does NOT support word-level timestamps
    - processor.py requires word timestamps for audio buffer extraction
    """
    STREAM_LIMIT = 290.0  # V2 supports up to 5 minutes streaming
    SAMPLE_RATE = 16000
    DEPTH = 2

    def __init__(self, audio_queue, transcript_queue, config, mediatype, interval):
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.config = config
        self.running = False
        self.audio_time = 0.0
        self.audio_interval = interval
        self.audio_file_duration = 0
        self.media_type = mediatype

        # V2 API requires project ID - read from credentials file
        credentials_path = cf.root_dir() + 'chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json'
        with open(credentials_path) as f:
            credentials = json.load(f)
        self.project_id = credentials.get('project_id')
        if not self.project_id:
            raise ValueError("project_id not found in credentials file")

        # Create client with regional endpoint (REQUIRED for V2)
        self.client = SpeechClient(
            client_options=ClientOptions(api_endpoint=API_ENDPOINT)
        )

        # Recognizer path uses regional location
        self.recognizer = f"projects/{self.project_id}/locations/{REGION}/recognizers/_"

    def start(self):
        self.running = True
        if self.media_type == 'audio':
            self.asr_thread = threading.Thread(
                target=self.processing,
                name="google-chirp2-speech"
            )
        elif self.media_type == 'video':
            self.asr_thread = threading.Thread(
                target=self.processing_wav_audio,
                name="google-chirp2-speech-wav"
            )
        self.asr_thread.daemon = True
        self.asr_thread.start()

    def stop(self):
        self.running = False

    def generator(self):
        """Yields audio chunks for streaming recognition."""
        generator_time = 0
        while self.running and generator_time < GoogleChirp2ASR.STREAM_LIMIT:
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
                generator_time += (len(chunk) / GoogleChirp2ASR.DEPTH) / GoogleChirp2ASR.SAMPLE_RATE
            yield b''.join(data)
        self.audio_time += generator_time

    def _convert_to_v1_format(self, result, audio_start_time):
        """
        Convert V2 result to V1-compatible format for processor.py.

        V2 uses: result.alternatives[0].words[i].start_offset/end_offset (Duration)
        V1 uses: result.alternatives[0].words[i].start_time/end_time (with .seconds/.nanos)
        """
        if not result.alternatives:
            return None

        v2_alt = result.alternatives[0]
        transcript_text = v2_alt.transcript

        # Convert words to V1 format with adjusted timestamps
        words = []
        for v2_word in v2_alt.words:
            # Create Word with V2's start_offset/end_offset
            word = Word(
                v2_word.word,
                v2_word.start_offset,
                v2_word.end_offset
            )
            # Adjust timestamps by audio_start_time (for stream reconnections)
            word.start_time.seconds, word.start_time.nanos = self._adjust_time(
                word.start_time.seconds,
                word.start_time.nanos,
                audio_start_time
            )
            word.end_time.seconds, word.end_time.nanos = self._adjust_time(
                word.end_time.seconds,
                word.end_time.nanos,
                audio_start_time
            )
            words.append(word)

        return TranscriptResult(transcript_text, words)

    def _adjust_time(self, seconds, nanos, offset):
        """Adjust timestamp by offset (matches V1 connector logic)."""
        adjusted_time = seconds + (nanos / NANO) + offset
        adjusted_nanos, adjusted_seconds = math.modf(adjusted_time)
        adjusted_nanos *= NANO
        adjusted_seconds += self.audio_file_duration
        return int(adjusted_seconds), int(adjusted_nanos)

    def process_responses(self, responses, audio_start_time):
        """Process V2 streaming responses."""
        for response in responses:
            for result in response.results:
                if not result.is_final:
                    continue
                if not result.alternatives:
                    continue
                if not result.alternatives[0].words:
                    # Skip results without word timestamps
                    logging.warning("Received result without word timestamps - skipping")
                    continue

                # Convert to V1 format and emit
                v1_result = self._convert_to_v1_format(result, audio_start_time)
                if v1_result:
                    self.transcript_queue.put(v1_result)

    def processing(self):
        """Main streaming processing loop."""
        logging.info(f'Google Chirp 2 ASR thread started for {self.config.auth_key}')

        # V2 recognition config with Chirp 2 and word timestamps
        recognition_config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=GoogleChirp2ASR.SAMPLE_RATE,
                audio_channel_count=1,
            ),
            language_codes=["en-US"],
            model="chirp_2",  # Chirp 2 supports streaming + word timestamps
            features=cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True,  # CRITICAL: Required for processor.py
                enable_automatic_punctuation=True,
            ),
        )

        streaming_config = cloud_speech.StreamingRecognitionConfig(
            config=recognition_config,
            streaming_features=cloud_speech.StreamingRecognitionFeatures(
                interim_results=False,
                enable_voice_activity_events=True,  # Built-in VAD
            ),
        )

        # Streaming loop - reconnects as needed (V2 supports longer streams)
        while self.running:
            try:
                def request_generator():
                    # First request: config only
                    yield cloud_speech.StreamingRecognizeRequest(
                        recognizer=self.recognizer,
                        streaming_config=streaming_config,
                    )
                    # Subsequent requests: audio data
                    for audio_chunk in self.generator():
                        yield cloud_speech.StreamingRecognizeRequest(
                            audio=audio_chunk
                        )

                responses = self.client.streaming_recognize(requests=request_generator())
                self.process_responses(responses, self.audio_time)

            except Exception as e:
                error_msg = str(e)
                if 'maximum allowed stream duration' in error_msg:
                    logging.warning(f'Stream max length exceeded for {self.config.auth_key}. Reconnecting...')
                elif 'DNS resolution failed' in error_msg:
                    logging.critical('Google ASR failed to reach DNS server. Shutting down...')
                    break
                else:
                    logging.warning(f'Error in Chirp 2 ASR for {self.config.auth_key}: {e}')

        logging.info(f'Google Chirp 2 ASR thread stopped for {self.config.auth_key}')
        self.transcript_queue.put(None)

    def processing_wav_audio(self):
        """Process WAV audio files (batch mode)."""
        logging.info(f'Google Chirp 2 WAV ASR thread started for {self.config.auth_key}')

        recognition_config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=GoogleChirp2ASR.SAMPLE_RATE,
                audio_channel_count=1,
            ),
            language_codes=["en-US"],
            model="chirp_2",  # Use chirp_2 for consistency
            features=cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True,  # CRITICAL
                enable_automatic_punctuation=True,
            ),
        )

        while self.running:
            try:
                if not self.audio_queue.empty():
                    audio_content = self.audio_queue.get()

                    request = cloud_speech.RecognizeRequest(
                        recognizer=self.recognizer,
                        config=recognition_config,
                        content=audio_content,
                    )

                    response = self.client.recognize(request=request)

                    for result in response.results:
                        if result.alternatives and result.alternatives[0].words:
                            v1_result = self._convert_to_v1_format(result, self.audio_time)
                            if v1_result:
                                self.transcript_queue.put(v1_result)

                    self.audio_file_duration += self.audio_interval

            except Exception as e:
                logging.warning(f'Error in Chirp 2 WAV ASR for {self.config.auth_key}: {e}')

        logging.info(f'Google Chirp 2 WAV ASR thread stopped for {self.config.auth_key}')
        self.transcript_queue.put(None)
