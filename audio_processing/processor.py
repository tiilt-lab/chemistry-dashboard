"""_summary_

Returns:
    _description_
"""

import time
import os
import logging
import threading
import callbacks
from speaker_metrics import speaker_metrics
from features_detector import features_detector
from keyword_detector import keyword_detector
from doa.doa_respeaker_v2_6mic_array import calculateDOA
from speaker_diarization.pyDiarization import clusterSpectralEmbeddings
from speaker_diarization.pyDiarization import embedSignal, checkFingerprints
from speaker_diarization.pyDiarization import getSpectralEmbeddings
import numpy as np
from joblib import load
from topic_modeling.topic_modeling import preprocess_transcript
import config as cf
# from source_seperation import source_seperation_pre_trained
# from server.topic_modeling.topicmodeling import get_topics_with_prob
# For converting nano seconds to seconds.
NANO = 1000000000


class AudioProcessor:
    def __init__(self, audio_buffer, transcript_queue, diarization_model,
                 semantic_model, config):
        self.audio_buffer = audio_buffer
        self.transcript_queue = transcript_queue
        self.mt_feats = np.array([])
        self.speakers = np.array([])
        self.signal = np.array([])
        self.max_speakers = 10
        self.embeddings = []
        self.embeddings_file = None
        self.diarization_model = diarization_model
        self.speaker_timings = []
        self.config = config
        self.fs = 16000
        self.running = False
        self.asr_complete = False
        self.running_processes = 0
        self.topic_model = None
        self.fingerprints = None
        self.cohesion_window = 20

        self.semantic_model = semantic_model
        logging.info("Start metrics process")
        self.speaker_metrics_process = speaker_metrics.SpeakerProcessor(
            config, self.semantic_model)

        cf.initialize()

    def start(self):
        self.running = True
        self.asr_complete = False
        self.running_processes = 0
        self.processing_thread = threading.Thread(target=self.process)
        self.processing_thread.daemon = True
        if self.config.topic_model:
            logging.info("Loading Topic Model")
            self.topic_model = load(os.path.join(
                "topicModels", f'{self.config.owner}_{self.config.topic_model}'))
            logging.info("Loading successful")
        self.processing_thread.start()

    def stop(self):
        self.running = False

    def __complete_callback(self):
        logging.info("completing callback")
        '''
        self.speaker_transcript_queue.put(None)
        self.speaker_metrics_process.join()
        self.speaker_metrics_process.close()
        '''
        if self.config.diarization:
            try:
                self.send_speaker_taggings()
            except Exception as ex:
                logging.info(ex)
            np.savetxt(cf.root_dir()+"chemistry-dashboard/audio_processing/speaker_diarization/results/{}.txt".format(
                time.strftime("%Y%m%d-%H%M%S")), self.speakers)

    def setSpeakerFingerprints(self, fingerprints):
        self.fingerprints = fingerprints
        logging.info("Set Speakers")
        self.speaker_metrics_process.setSpeakers(self.fingerprints)

    def send_speaker_taggings(self):
        processing_timer = time.time()
        results = []
        spectralEmbeddings, n_speakers = getSpectralEmbeddings(self.embeddings)
        self.speakers, speaker_class_names, cls_ctrs = clusterSpectralEmbeddings(
            spectralEmbeddings, n_speakers)
        for i in range(0, len(self.speakers)):
            results.append({
                'speaker': 'Speaker {0}'.format(self.speakers[i]),
                'start': self.embeddings[i]['start'],
                'end': self.embeddings[i]['end']
            })

        # Convert results into expected JSON format.
        taggings = {}
        taggings["results"] = results

        processing_time = time.time() - processing_timer
        logging.info(taggings)  # DEBUG: Prints the converted speaker timings.
        taggings_posted = callbacks.post_tagging(
            self.config.auth_key, taggings, self.embeddings_file)
        if taggings_posted:
            logging.info('Tagging results posted successfully for  {0} (Processing time: {1})'.format(
                self.config.auth_key, processing_time))
        else:
            logging.info('Processing results FAILED to post for tagging {0} '.format(
                self.config.auth_key))

    def float_to_timestamp(self, t):
        hours = int(t / 3600)
        minutes = int((t % 3600) / 60)
        seconds = int((t % 60))
        milliseconds = int((t % 1) * 1000)
        return '{0}:{1}:{2}:{3}'.format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2), str(milliseconds).zfill(4))

    def process(self):
        logging.info('Processing thread started for {0}.'.format(
            self.config.auth_key))
        self.embeddings_file = self.config.embeddings_file
        while not self.asr_complete:
            transcript_data = self.transcript_queue.get()
            if transcript_data is None:
                self.asr_complete = True
            else:
                # Gather audio data related to the transcript.
                words = transcript_data.alternatives[0].words
                start_time = words[0].start_time.seconds + \
                    (words[0].start_time.nanos / NANO)
                end_time = words[-1].end_time.seconds + \
                    (words[-1].end_time.nanos / NANO)
                transcript_audio_data = self.audio_buffer.extract(
                    start_time, end_time)
                # Start processing thread for DoA, keywords, feature, etc.
                self.running_processes += 1
                transcript_thread = threading.Thread(target=self.process_transcript, args=(
                    transcript_data, transcript_audio_data, start_time, end_time))
                transcript_thread.daemon = True
                transcript_thread.start()
        if self.running_processes == 0:
            self.__complete_callback()
        logging.info('Processing thread stopped for {0}.'.format(
            self.config.auth_key))

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
                keywords = keyword_detector.detect_keywords(
                    transcript_text, self.config.keywords)

            # Get Topics
            topics = None
            topic_id = -1
            if self.topic_model:
                logging.info("Text for topic modeling")
                logging.info(transcript_text)
                preprocessed = preprocess_transcript(transcript_text, [""])
                logging.info("Preprocessed")
                logging.info(preprocessed)
                logging.info(self.topic_model.id2word)
                text2bow = self.topic_model.id2word.doc2bow(preprocessed)
                logging.info("Corpus")
                logging.info(text2bow)
                if len(text2bow):
                    topics = self.topic_model[text2bow]
                    logging.info("Topics distribution: ")
                    logging.info(topics)
                    #    topics = get_topics_with_prob(transcript_text)
                    if len(topics) > 0:
                        max = 0
                        for topic in topics:
                            if topic[1] > max:
                                topic_id = topic[0]
                logging.info(topic_id)

            # Get DoA
            doa = None
            if self.config.doa and self.config.channels == 6:
                word_timings = [(word.start_time.seconds + (word.start_time.nanos / NANO),
                                 word.end_time.seconds + (word.end_time.nanos / NANO)) for word in words]
                doa = calculateDOA(start_time, audio_data, word_timings,
                                   16000, self.config.channels, self.config.depth)

            features = None
            if self.config.features:
                features = features_detector.detect_features(transcript_text)

            start_time += self.config.start_offset
            end_time += self.config.start_offset

            # Perform Speaker Diarization
            speaker_tag = None
            speaker_id = -1
            if self.config.diarization and self.fingerprints and len(self.fingerprints):
                speaker_tag, speaker_id = checkFingerprints(
                        audio_data, self.fingerprints, self.diarization_model)
                self.speaker_metrics_process.process_transcript(
                    {
                        'source': self.config.auth_key,
                        'start_time': start_time,
                        'end_time': end_time,
                        'transcript': transcript_text,
                        'doa': doa,
                        'questions': questions,
                        'keywords': keywords,
                        'features': features,
                        'topic_id': topic_id,
                        'speaker_tag': speaker_tag,
                        'speaker_id': speaker_id
                    })
            else:
                if self.config.diarization:
                    if len(self.embeddings) == 0 and self.embeddings_file is not None:
                        try:
                            self.embeddings = np.load(
                                self.embeddings_file).tolist()
                        except Exception as e:
                            logging.error(
                                "Unable to load embeddings file: %s", e)
                            self.embeddings = []
                    elif self.embeddings_file is None:
                        self.embeddings_file = time.strftime(
                            "%Y%m%d-%H%M%S")+".npy"
                    embedding = embedSignal(audio_data, self.diarization_model)
                    self.embeddings.append({
                        'embedding': embedding,
                        'start': start_time,
                        'end': end_time,
                    })

                    np.save(self.embeddings_file, np.array(self.embeddings))
                success, transcript_id = callbacks.post_transcripts(
                    self.config.auth_key, start_time, end_time,
                    transcript_text, doa, questions, keywords,
                    features, topic_id, speaker_tag, speaker_id)

                processing_time = time.time() - processing_timer

                if success:
                    logging.info( f"Processing results posted successfully for client {self.config.auth_key} (Processing time: {processing_time}) @ {start_time} for transcript {transcript_id}")
                else:
                    logging.warning(f"Processing results FAILED to post for client {self.config.auth_key} (Processing time: {processing_time})")

            # Get source seperation
            # if self.config.source_seperation:
            #   source_seperation = source_seperation_pre_trained(audio_data)

        except Exception as e:
            logging.error("Processing FAILED for client %d: %s",
                          self.config.auth_key, e)

        # Check if this was the final process of the transmission.
        self.running_processes -= 1
        if self.asr_complete and self.running_processes == 0:
            self.__complete_callback()
