import numpy as np
#from sentence_transformers import SentenceTransformer
import queue
import logging

'''
SpeakerProcessor

Perfrom textual analysis of each speakers data using the transcripts and diarization output.
Follows Group Communication Analysis study using matrix operations to optimize the performance
as the discussion continues
'''


class SpeakerProcessor:
    def __init__(self, speaker_transcript_queue, speakers, window, model, config):

        self.speaker_transcript_queue = speaker_transcript_queue
        self.participants = len(speakers)
        self.speakers = speakers
        self.indicies = {k: i for i ,k in enumerate(speakers)}
        self.total_contributions = 0
        self.asr_complete = False
        self.model = model

        self.semantic_embeddings = np.array([])
        self.subspace_basis = np.array([])
        self.tau_window = window

        self.contributions = np.zeros(self.participants+1, dtype=int)
        prev_window_speakers =  queue.Queue()
        window_lagged_contributions = np.zeros((window, self.participants+1, self.self.participants+1), dtype=int)
        xi_sums = np.zeros((window, self.participants+1, self.participants+1), dtype=float)
        resp_vals = np.zeros((self.participants+1, self.participants+1), dtype=float)
        total_new = np.zeros(self.participants+1, dtype=float)

        ignore_diag = np.ones((self.participants+1, self.participants+1), dtype=bool)
        np.fill_diagonal(ignore_diag, 0)

        participation_scores = np.zeros((self.participants+1), dtype=float)
        interal_cohesion = np.zeros((self.participants+1), dtype=float)
        overall_responsivity = np.zeros((self.participants+1), dtype=float)
        social_impact = np.zeros((self.participants+1), dtype=float)
        newness = total_new

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
