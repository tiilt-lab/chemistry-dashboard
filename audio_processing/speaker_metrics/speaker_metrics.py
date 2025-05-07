import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os
import multiprocessing as mp
from multiprocessing.process import AuthenticationString
import time
import callbacks

'''
SpeakerProcessor

Perfrom textual analysis of each speakers data using the transcripts and diarization output.
Follows Group Communication Analysis study using matrix operations to optimize the performance
as the discussion continues
'''

normalizeVector = lambda v: np.divide(v, np.linalg.norm(v))
projection = lambda v1, v2 : np.multiply(np.dot(v2, v1)/np.dot(v1, v1), v1)

class SpeakerProcessor:

    speakers = None
    participants = 0
    indicies = None

    def __init__(self, config, semantic_model):

        logging.info("[Speaker_Metrics]Inside speaker metric init")
        self.total_contributions = 0
        self.asr_complete = False
        self.auth_key = config.auth_key
        logging.info(self.auth_key)
        logging.info('[Speaker_Metrics]Loaded semenatic model')

        self.running_process = None
        self.running = False

        self.embeddings = np.array([])
        self.subspace_basis = np.array([])
        self.tau_window = 20

        self.length = 0
        self.semantic_model = semantic_model

    def setSpeakers(self, speakers):
      if speakers is None:
         return
      self.speakers = speakers
      self.participants = len(speakers)
      self.indicies = {k: i for i ,k in enumerate(speakers)}

      self.contributions = np.zeros(self.participants+1, dtype=int)
      self.prev_window_speakers =  []
      self.window_lagged_contributions = np.zeros((self.tau_window, self.participants+1, self.participants+1), dtype=int)
      self.xi_sums = np.zeros((self.tau_window, self.participants+1, self.participants+1), dtype=float)
      self.resp_vals = np.zeros((self.participants+1, self.participants+1), dtype=float)
      self.total_new = np.zeros(self.participants+1, dtype=float)

      self.ignore_diag = np.ones((self.participants+1, self.participants+1), dtype=bool)
      np.fill_diagonal(self.ignore_diag, 0)

      self.participation_scores = np.zeros((self.participants+1), dtype=float)
      self.internal_cohesion = np.zeros((self.participants+1), dtype=float)
      self.overall_responsivity = np.zeros((self.participants+1), dtype=float)
      self.social_impact = np.zeros((self.participants+1), dtype=float)
      self.newness = self.total_new
      self.communication_density = np.zeros((self.participants+1), dtype=float)

    def calculateCohesionSums(self, speaker, embedding, model):
      if self.length >= self.tau_window:
        for i in range(0, self.tau_window):
            prev_speaker =  self.indicies[self.prev_window_speakers[i]] + 1 if self.prev_window_speakers[i] != -1 else 0
            self.xi_sums[i][prev_speaker][speaker] +=  model.similarity(self.embeddings[self.length-i-1], embedding)
            self.window_lagged_contributions[i][prev_speaker][speaker] += 1
        self.prev_window_speakers.pop(0)
      else:
         for i in range(0, self.length):
            prev_speaker = self.indicies[self.prev_window_speakers[i]] + 1 if self.prev_window_speakers[i] != -1 else 0
            self.xi_sums[i][prev_speaker][speaker] += model.similarity(self.embeddings[self.length-i-1], embedding)
            self.window_lagged_contributions[i][prev_speaker][speaker] += 1

      with np.errstate(divide='ignore', invalid='ignore'):
          cross_cohesion = np.divide(self.xi_sums, self.window_lagged_contributions)
          cross_cohesion = np.nan_to_num(cross_cohesion)

      return cross_cohesion

    def subspaceProjection(self, s, v):
        proj = 0
        for vector in s:
            proj += projection(vector, v)
        return proj

    def processResponsivity(self, cross_cohesion):
        responsivity = np.divide(np.sum(cross_cohesion, axis=0), self.tau_window)
        self.internal_cohesion = np.diagonal(responsivity)
        self.social_impact = np.divide(np.sum(responsivity, axis=0, where=self.ignore_diag), self.participants)
        self.overall_responsivity = np.divide(np.sum(responsivity, axis=1, where=self.ignore_diag), self.participants)

    def calculateNewness(self, embedding, speaker):
        self.embeddings = np.concatenate((self.embeddings, np.array([embedding])))
        given_data = self.subspaceProjection(self.subspace_basis, embedding)
        new_data = np.array([embedding - given_data])
        self.total_new[speaker] += np.linalg.norm(new_data)/(np.linalg.norm(given_data) + np.linalg.norm(new_data))
        normalized_new_data = normalizeVector(new_data)
        self.subspace_basis = np.concatenate((self.subspace_basis, normalized_new_data), axis = 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            self.newness = np.divide(self.total_new, self.contributions)
            self.newness = np.nan_to_num(self.newness)

    def start(self):
        self.running = True
        self.asr_complete = False

    def stop(self):
        self.running = False
        self.asr_complete = True

    def process_transcript(self, speaker_transcript_data):
      try:
        processing_timer = time.time()
        speaker_ids = list(self.speakers.keys())

        speaker = speaker_transcript_data['speaker_id']
        transcript = speaker_transcript_data['transcript']
        index = self.indicies[speaker] + 1 if speaker != -1 else 0
        self.contributions[index] += 1

        embedding = self.semantic_model.encode(transcript)

        if self.length > 0:
          cross_cohesion = self.calculateCohesionSums(index, embedding, self.semantic_model)
          self.processResponsivity(cross_cohesion)
          self.calculateNewness(embedding, index)

        else:
          self.embeddings = np.array([embedding])
          self.subspace_basis = normalizeVector(self.embeddings)
          self.total_new[index] += 1

        self.length += 1
        self.prev_window_speakers.append(speaker)
        self.participation_scores = np.subtract(np.multiply(np.divide(self.contributions, self.length), self.participants), 1)

        processing_time =  time.time() - processing_timer

        success = callbacks.post_speaker_transcript_metrics(speaker_transcript_data,
                                                  speaker_ids,
                                                  self.participation_scores.tolist(),
                                                  self.internal_cohesion.tolist(),
                                                  self.overall_responsivity.tolist(),
                                                  self.social_impact.tolist(),
                                                  self.newness.tolist(),
                                                  self.communication_density.tolist())

        if success:
           logging.info('[Speaker_Metrics]Processing posted successfully for client {0} (Processing time: {1}) @ {2}'.format(self.auth_key, processing_time, processing_timer))
        else:
           logging.warning('[Speaker_Metrics]Processing results FAILED to post for client {0} (Processing time: {1})'.format(self.auth_key, processing_time))
      except Exception as e:
         logging.error('[Speaker Metrics]Processing FAILED for client {0}: {1}'.format(auth_key, e))



def process(processing_queue, speaker_transcript_queue, model):

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


    logging.info("[Speaker_Metrics]Init speaker metrics processor")
    config = processing_queue.get()
    processor = SpeakerProcessor(config)
    auth_key = processor.auth_key
    processor.start()

    if processor:
      logging.info('[Speaker_Metrics]Speaker metric Process started for {0}.'.format(auth_key))
      speakers = processing_queue.get()

      if speakers:
        logging.info('[Speaker_Metrics]Speaker metric Process for {0} processed fingerprints.'.format(auth_key))
        processor.setSpeakers(speakers)
        speaker_ids = list(speakers.keys())

        while processor.running and not processor.asr_complete :
            try:
              speaker_transcript_data = speaker_transcript_queue.get()
              processing_timer = time.time()

              if speaker_transcript_data is None:
                  logging.info("[Speaker_Metrics]Attempting to stop")
                  processor.stop()

              else:
                speaker = speaker_transcript_data['speaker_id']
                transcript = speaker_transcript_data['transcript']
                index = processor.indicies[speaker] + 1 if speaker != -1 else 0
                processor.contributions[index] += 1

                embedding = model.encode(transcript)

                if processor.length > 0:
                  cross_cohesion = processor.calculateCohesionSums(index, embedding, model)
                  processor.processResponsivity(cross_cohesion)
                  processor.calculateNewness(embedding, index)

                else:
                  processor.embeddings = np.array([embedding])
                  processor.subspace_basis = normalizeVector(processor.embeddings)
                  processor.total_new[index] += 1

                processor.length += 1
                processor.prev_window_speakers.append(speaker)
                processor.participation_scores = np.subtract(np.multiply(np.divide(processor.contributions, processor.length), processor.participants), 1)

                processing_time =  time.time() - processing_timer

                success = callbacks.post_speaker_transcript_metrics(speaker_transcript_data,
                                                         speaker_ids,
                                                         processor.participation_scores.tolist(),
                                                         processor.internal_cohesion.tolist(),
                                                         processor.overall_responsivity.tolist(),
                                                         processor.social_impact.tolist(),
                                                         processor.newness.tolist(),
                                                         processor.communication_density.tolist())

                if success:
                   logging.info('[Speaker_Metrics]Processing posted successfully for client {0} (Processing time: {1}) @ {2}'.format(auth_key, processing_time, processing_timer))
                else:
                   logging.warning('[Speaker_Metrics]Processing results FAILED to post for client {0} (Processing time: {1})'.format(auth_key, processing_time))

            except Exception as e:
              logging.error('[Speaker Metrics]Processing FAILED for client {0}: {1}'.format(auth_key, e))


    logging.info('[Speaker_Metrics]Speaker metric Process stopped for {0}.'.format(auth_key))
