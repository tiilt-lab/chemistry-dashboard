import time
import os
import logging
import threading
import callbacks
from features_detector import features_detector
from keyword_detector import keyword_detector
from doa.doa_respeaker_v2_6mic_array import calculateDOA
from speaker_diarization.pyDiarization import clusterEmbeddings, clusterSpectralEmbeddings, embedSignal, getSpectralEmbeddings
import numpy as np
from speechbrain.pretrained import SpeakerRecognition
import time
from gensim.models.ldamodel import LdaModel
from joblib import load
from topic_modeling.topic_modeling import preprocess_transcript
#from source_seperation import source_seperation_pre_trained
#from server.topic_modeling.topicmodeling import get_topics_with_prob

# For converting nano seconds to seconds.
NANO = 1000000000

class AudioProcessor:
    def __init__(self, audio_buffer, transcript_queue, config):
        self.audio_buffer = audio_buffer
        self.transcript_queue = transcript_queue
        self.mt_feats = np.array([])
        self.speakers = np.array([])
        self.signal = np.array([])
        self.max_speakers = 10
        self.embeddings = []
        self.embeddingsFile = None
        self.diarization_model = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="./pretrained_ecapa")
        self.speaker_timings = []
        self.config = config
        self.fs = 16000
        self.running = False
        self.asr_complete = False
        self.running_processes = 0
        self.topic_model = None

    def start(self):
        self.running = True
        self.asr_complete = False
        self.running_processes = 0
        self.processing_thread = threading.Thread(target=self.process)
        self.processing_thread.daemon = True
        if self.config.topic_model:
            logging.info("Loading Topic Model")
            self.topic_model = load(os.path.join("topicModels", f'{self.config.owner}_{self.config.topic_model}'))
            logging.info("Loading successful")
        self.processing_thread.start()

    def stop(self):
        self.running = False

    def __complete_callback(self):
        logging.info("completing callback")
        logging.info(self.config.diarization)
        if self.config.diarization:
            try:
                self.send_speaker_taggings()
            except Exception as ex:
                logging.info(ex)
            np.savetxt("/var/lib/chemistry-dashboard/audio_processing/speaker_diarization/results/{}.txt".format(time.strftime("%Y%m%d-%H%M%S")), self.speakers)

    def send_speaker_taggings(self):
        # Parse results from embeddings list.
        #self.embeddings.sort(key=lambda x: x['start'])
        processing_timer = time.time()
        logging.info("tagging")
        results = []
        spectralEmbeddings, n_speakers = getSpectralEmbeddings(self.embeddings)
        self.speakers, speaker_class_names, cls_ctrs = clusterSpectralEmbeddings(spectralEmbeddings, n_speakers)
        logging.info("Tagged")
        logging.info(n_speakers)
        logging.info(self.speakers)
        logging.info(len(self.embeddings))
        for i in range(0, len(self.speakers)):
          results.append({
              'speaker': 'Speaker {0}'.format(self.speakers[i]),
              'start': self.embeddings[i]['start'],
              'end': self.embeddings[i]['end']
        })
        logging.info("created results array")
        logging.info(results)
        # Convert results into expected JSON format.
        taggings = {}
        taggings["results"] = results
        '''
        for i in range(0, len(results)):
            result = results[i]
            speaker = 'Speaker {0}'.format(result['speaker'])
            timing = [self.float_to_timestamp(result['start']), self.float_to_timestamp(result['end'])]
            if not speaker in taggings:
                taggings[speaker] = [timing]
            else:
                taggings[speaker].append(timing)
        '''
        processing_time = time.time() - processing_timer
        logging.info(taggings) # DEBUG: Prints the converted speaker timings.
        taggings_posted = callbacks.post_tagging(self.config.auth_key, taggings, self.embeddingsFile)
        if taggings_posted:
            logging.info('Processing results posted successfully for tagging {0} (Processing time: {1})'.format(self.config.auth_key, processing_time))
        else:
            logging.info('Processing results FAILED to post for tagging {0} '.format(self.config.auth_key))

    def float_to_timestamp(self, t):
        hours = int(t / 3600)
        minutes = int((t % 3600) / 60)
        seconds = int((t % 60))
        milliseconds = int((t % 1) * 1000)
        return '{0}:{1}:{2}:{3}'.format(str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2), str(milliseconds).zfill(4))

    def process(self):
        logging.info('Processing thread started for {0}.'.format(self.config.auth_key))
        self.embeddingsFile = self.config.embeddingsFile
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
                word_timings = [(word.start_time.seconds + (word.start_time.nanos / NANO), word.end_time.seconds + (word.end_time.nanos / NANO)) for word in words]
                doa = calculateDOA(start_time, audio_data, word_timings, 16000, self.config.channels, self.config.depth)

            #Perform Speaker Diarization
            if self.config.diarization:
                if len(self.embeddings) == 0 and self.embeddingsFile != None:
                    try:
                      self.embeddings = np.load(self.embeddingsFile).tolist()
                    except:
                      self.embeddings = []
                elif self.embeddingsFile == None:
                    self.embeddingsFile = time.strftime("%Y%m%d-%H%M%S")+".npy"
                embedding = embedSignal(audio_data, self.diarization_model)
                self.embeddings.append({
                    'embedding': embedding,
                    'start': start_time + self.config.start_offset,
                    'end': end_time + self.config.start_offset,
                })
                np.save(self.embeddingsFile, np.array(self.embeddings))

            # Get Features
            features = None
            if self.config.features:
                features = features_detector.detect_features(transcript_text)

            processing_time = time.time() - processing_timer
            start_time += self.config.start_offset
            end_time += self.config.start_offset
            success = callbacks.post_transcripts(self.config.auth_key, start_time, end_time, transcript_text, doa, questions, keywords, features, topic_id)

            if success:
                logging.info('Processing results posted successfully for client {0} (Processing time: {1}) @ {2}'.format(self.config.auth_key, processing_time, start_time))
                if self.config.diarization and (len(self.embeddings) > 3):
                  self.send_speaker_taggings()

            else:
                logging.warning('Processing results FAILED to post for client {0} (Processing time: {1})'.format(self.config.auth_key, processing_time))

            #Get source seperation
            #if self.config.source_seperation:
            #   source_seperation = source_seperation_pre_trained(audio_data)

        except Exception as e:
            logging.error('Processing FAILED for client {0}: {1}'.format(self.config.auth_key, e))

        # Check if this was the final process of the transmission.
        self.running_processes -= 1
        if self.asr_complete and self.running_processes == 0:
            self.__complete_callback()
