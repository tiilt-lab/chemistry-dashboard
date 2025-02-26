import numpy as np
#from sentence_transformers import SentenceTransformer
import logging
import multiprocessing as mp

'''
SpeakerProcessor

Perfrom textual analysis of each speakers data using the transcripts and diarization output.
Follows Group Communication Analysis study using matrix operations to optimize the performance
as the discussion continues
'''

class SpeakerProcessor:
    normalizeVector = lambda v: np.divide(v, np.linalg.norm(v))

    projection = lambda v1, v2 : np.multiply(np.dot(v2, v1)/np.dot(v1, v1), v1)

    def __init__(self, speaker_transcript_queue, speakers, window, model, config):

        self.speaker_transcript_queue = speaker_transcript_queue
        self.participants = len(speakers)
        self.speakers = speakers
        self.indicies = {k: i for i ,k in enumerate(speakers)}
        self.total_contributions = 0
        self.model = model
        self.asr_complete = False
        self.config = config
        self.running_process = None
        self.running = False

        self.embeddings = np.array([])
        self.subspace_basis = np.array([])
        self.tau_window = window

        self.contributions = np.zeros(self.participants+1, dtype=int)
        self.prev_window_speakers =  []
        self.window_lagged_contributions = np.zeros((window, self.participants+1, self.participants+1), dtype=int)
        self.xi_sums = np.zeros((window, self.participants+1, self.participants+1), dtype=float)
        self.resp_vals = np.zeros((self.participants+1, self.participants+1), dtype=float)
        self.total_new = np.zeros(self.participants+1, dtype=float)

        self.ignore_diag = np.ones((self.participants+1, self.participants+1), dtype=bool)
        np.fill_diagonal(self.ignore_diag, 0)

        self.participation_scores = np.zeros((self.participants+1), dtype=float)
        self.interal_cohesion = np.zeros((self.participants+1), dtype=float)
        self.overall_responsivity = np.zeros((self.participants+1), dtype=float)
        self.social_impact = np.zeros((self.participants+1), dtype=float)
        self.newness = self.total_new
        self.length = 0

    def process(self):
        logging.info('Speaker metric Process started for {0}.'.format(self.config.auth_key))
        while not self.asr_complete:
            speaker_transcript_data = self.speaker_transcript_queue.get()

            if speaker_transcript_data is None:
                self.asr_complete = True

            else:
              speaker = speaker_transcript_data[0]
              transcipt = speaker_transcript_data[1]
              index = self.indicies[speaker] + 1 if speaker != -1 else 0
              self.contributions[index] += 1

              embedding = self.model.encode(transcipt)

              if self.length > 0:
                cross_cohesion = self.calculateCohesionSums(speaker, index)
                self.processResponsivity(cross_cohesion)
                self.calculateNewness(embedding, index)

              else:
                self.embeddings = np.array([embedding])
                self.subspace_basis = self.normalizeVector(self.embeddings)
                self.total_new[index] += 1

              self.length += 1
              self.prev_window_speakers.append(speaker)
              self.participation_scores = np.subtract(np.multiply(np.divide(self.contributions, self.length), self.participants), 1)

        self.stop()
        logging.info('Speaker metric Process stopped for {0}.'.format(self.config.auth_key))

    def calculateCohesionSums(self, speaker, embedding):
      if self.length > 1:
        for i in range(0, self.tau_window):
            prev_speaker =  self.indicies[self.prev_window_speakers[i]]
            self.xi_sums[i][prev_speaker][speaker] +=  self.model.similarity(self.embeddings[self.length-i-1], embedding)
            self.window_lagged_contributions[i][prev_speaker][speaker] += 1
        self.prev_window_speakers.pop(0)
      else:
         for i in range(0, self.length):
            prev_speaker = self.indicies[self.prev_window_speakers[i]]
            self.xi_sums[i][prev_speaker][speaker] += self.model.similarity(self.embeddings[self.length-i-1], embedding)
            self.window_lagged_contributions[i][prev_speaker][speaker] += 1

      with np.errstate(divide='ignore', invalid='ignore'):
          cross_cohesion = np.divide(self.xi_sums, self.window_lagged_contributions)
          cross_cohesion = np.nan_to_num(cross_cohesion)

      return cross_cohesion

    def subspaceProjection(self, s, v):
        proj = 0
        for vector in s:
            proj += self.projection(vector, v)
        return proj

    def processResponsivity(self, cross_cohesion):
        responsivity = np.divide(np.sum(cross_cohesion, axis=0), self.tau_window)
        self.internal_cohesion = np.diagonal(responsivity)
        self.social_impact = np.divide(np.sum(responsivity, axis=0, where=self.ignore_diag), self.participants)
        self.overall_responsivity = np.divide(np.sum(responsivity, axis=1, where=self.ignore_diag), self.participants)

    def calculateNewness(self, embedding, speaker):
        self.embeddings = np.concatenate((self.embeddings, np.array([embedding])))
        given_data = self.subspaceProjection(curr_basis, embedding)
        new_data = np.array([embedding - given_data])
        self.total_new[speaker] += np.linalg.norm(new_data)/(np.linalg.norm(given_data) + np.linalg.norm(new_data))
        normalized_new_data = self.normalizeVector(new_data)
        curr_basis = np.concatenate((curr_basis, normalized_new_data), axis = 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            self.newness = np.divide(self.total_new, self.contributions)

    def start(self):
        if(self.running):
           self.stop()
        self.running = True
        self.asr_complete = False
        self.running_process = mp.Process(target=self.process, args=())
        self.running_process.start()

    def stop(self):
        self.running = False
        self.running_process.join()
