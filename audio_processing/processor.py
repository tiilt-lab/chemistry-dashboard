from datetime import datetime
import time
import logging
import threading
import callbacks
from features_detector import features_detector
from keyword_detector import keyword_detector
from doa.doa_respeaker_v2_6mic_array import calculateDOA
from speaker_diarization.pyDiarization import speakerDiarization
from speaker_diarization.pyannoteDiarization import newSpeakerDiarization
import numpy as np
import time

# For converting nano seconds to seconds.
NANO = 1000000000

class AudioProcessor:
    def __init__(self, audio_buffer, transcript_queue, config):
        self.audio_buffer = audio_buffer
        self.transcript_queue = transcript_queue
        # self.mt_feats = np.array([])
        self.speakers = np.array([])
        self.speaker_timings = []
        self.fs = config.sample_rate
        self.config = config
        self.running = False
        self.asr_complete = False
        self.running_processes = 0
        self.chunkNum = 0 # only 0 if new audrio processor instance is init per recording
        self.filename = datetime.now()

    def start(self):
        self.running = True
        self.asr_complete = False
        self.running_processes = 0
        self.processing_thread = threading.Thread(target=self.process)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop(self):
        self.running = False

    def __complete_callback(self):
        if self.config.diarization:
            try:
                self.send_speaker_taggings()
            except Exception as ex:
                logging.info(ex)
            np.savetxt("/var/lib/chemistry-dashboard/audio_processing/speaker_diarization/results/{}.txt".format(time.strftime("%Y%m%d-%H%M%S")), self.speakers)

    def send_speaker_taggings(self):
        # Convert speakertimings into expected JSON format.
        taggings = {}
        for i in range(0, len(self.speaker_timings)):
            result = self.speaker_timings[i]
            speaker = 'Speaker {0}'.format(result['speaker'])
            timing = [self.float_to_timestamp(result['start']), self.float_to_timestamp(result['end'])]
            if not speaker in taggings:
                taggings[speaker] = [timing]
            else:
                taggings[speaker].append(timing)
        logging.info(taggings) # DEBUG: Prints the converted speaker timings.
        callbacks.post_tagging(self.config.auth_key, taggings)

    def float_to_timestamp(self, t):
        hours = int(t / 3600)
        minutes = int((t % 3600) / 60)
        seconds = int((t % 60))
        milliseconds = int((t % 1) * 1000)
        return '{0}:{1}:{2}:{3}'.format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2), str(milliseconds).zfill(4))

    def process(self):
        logging.info('Processing thread started for {0}.'.format(self.config.auth_key))
        while not self.asr_complete:
            transcript_data = self.transcript_queue.get()
            if transcript_data is None:
                self.asr_complete = True
            else:
                # Gather audio data related to the transcript.
                words = transcript_data.alternatives[0].words
                start_time = words[0].start_time.seconds + (words[0].start_time.nanos / NANO)
                end_time = words[-1].end_time.seconds + (words[-1].end_time.nanos / NANO)
                transcript_audio_data = self.audio_buffer.extract(start_time, end_time)

                # Start processing thread for DoA, keywords, feature, etc.
                self.running_processes += 1
                transcript_thread = threading.Thread(target=self.process_transcript, args=(transcript_data, transcript_audio_data, start_time, end_time))
                transcript_thread.daemon = True
                transcript_thread.start()
        if self.running_processes == 0:
            self.__complete_callback()
        logging.info('Processing thread stopped for {0}.'.format(self.config.auth_key))

    # Processes a transcript and its related audio data.
    def process_transcript(self, transcript_data, audio_data, start_time, end_time):
        try:
            processing_timer = time.time()
            words = transcript_data.alternatives[0].words

            # Get Transcripts and Questions
            transcript_text = None
            questions = None
            if self.config.transcribe:
                transcript_text = transcript_data.alternatives[0].transcript
                questions = features_detector.detect_questions(transcript_text)

            # Get Keywords.
            keywords = None
            if self.config.keywords:
                keywords = keyword_detector.detect_keywords(transcript_text, self.config.keywords)

            # Get DoA
            doa = None
            if self.config.doa and self.config.channels == 6:
                word_timings = [(word.start_time.seconds + (word.start_time.nanos / NANO), word.end_time.seconds + (word.end_time.nanos / NANO)) for word in words]
                doa = calculateDOA(start_time, audio_data, word_timings, 16000, self.config.channels, self.config.depth)

            #Perform Speaker Diarization
            if self.config.diarization:
                # audio_data comes from buffer.extract()
                sample_width = 2 # not sure if this is true
                n_channels = 1 # how to decide this?
                n_speakers, timings, self.chunkNum = newSpeakerDiarization(
                    audio_data, sample_width, self.fs, n_channels, f'dia_{self.filename}.wav', self.chunkNum)
                
                self.speaker_timings = timings


            # Get Features
            features = None
            if self.config.features:
                features = features_detector.detect_features(transcript_text)

            processing_time = time.time() - processing_timer
            start_time += self.config.start_offset
            end_time += self.config.start_offset
            success = callbacks.post_transcripts(self.config.auth_key, start_time, end_time, transcript_text, doa, questions, keywords, features)

            if success:
                logging.info('Processing results posted successfully for client {0} (Processing time: {1}) @ {2}'.format(self.config.auth_key, processing_time, start_time))

            else:
                logging.warning('Processing results FAILED to post for client {0} (Processing time: {1})'.format(self.config.auth_key, processing_time))

        except Exception as e:
            logging.error('Processing FAILED for client {0}: {1}'.format(self.config.auth_key, e))

        # Check if this was the final process of the transmission.
        self.running_processes -= 1
        if self.asr_complete and self.running_processes == 0:
            self.__complete_callback()