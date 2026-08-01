import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import os
import multiprocessing as mp
from multiprocessing.process import AuthenticationString
import time
import callbacks
import traceback

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

    def __init__(self, config, semantic_model,usedby="audio_processor"):

        logging.info("[Speaker_Metrics]Inside speaker metric init")
        self.total_contributions = 0
        self.asr_complete = False
        self.auth_key = config.auth_key
        logging.info(self.auth_key)
        logging.info('[Speaker_Metrics]Loaded semenatic model')

        self.usedby = usedby
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
      logging.info("speakers are {0}".format(self.indicies))

      # if self.usedby == "speaker metric processor":
      #    self.contributions = np.zeros(self.participants, dtype=int)
      # else:   
      #   self.contributions = np.zeros(self.participants+1, dtype=int)

      self.contributions = np.zeros(self.participants, dtype=int)  

      self.prev_window_speakers =  []
      self.embedding_speakers = []

      self.window_lagged_contributions = np.zeros((self.tau_window, self.participants, self.participants), dtype=int) #np.zeros((self.tau_window, self.participants+1, self.participants+1), dtype=int)
      self.xi_sums = np.zeros((self.tau_window, self.participants, self.participants), dtype=float) #np.zeros((self.tau_window, self.participants+1, self.participants+1), dtype=float)
      self.resp_vals = np.zeros((self.participants, self.participants), dtype=float) #np.zeros((self.participants+1, self.participants+1), dtype=float)
      self.total_new = np.zeros(self.participants, dtype=float) #np.zeros((self.participants+1), dtype=float)

      self.ignore_diag = np.ones((self.participants, self.participants), dtype=bool) #np.ones((self.participants+1, self.participants+1), dtype=bool)
      np.fill_diagonal(self.ignore_diag, 0)

      self.participation_scores = np.zeros((self.participants), dtype=float) #np.zeros((self.participants+1), dtype=float)
      self.internal_cohesion = np.zeros((self.participants), dtype=float) #np.zeros((self.participants+1), dtype=float)
      self.overall_responsivity = np.zeros((self.participants), dtype=float) #np.zeros((self.participants+1), dtype=float)
      self.social_impact = np.zeros((self.participants), dtype=float) #np.zeros((self.participants+1), dtype=float)
      self.newness = self.total_new
      self.communication_density = np.zeros((self.participants), dtype=float) #np.zeros((self.participants+1), dtype=float)

    def calculateCohesionSums(self, speaker, embedding, model):
      current_speaker = speaker
      min_lag = min(self.length, self.tau_window)
      for i in range(0, min_lag):
          lag = i + 1
          prev_speaker =  self.indicies[self.prev_window_speakers[-lag]]  #self.indicies[self.prev_window_speakers[i]] + 1 if self.prev_window_speakers[i] != -1 else 0
          sim = model.similarity(self.embeddings[-lag], embedding)
          # logging.info("simillarity is {0} for lag {1}".format(sim,lag))
          self.xi_sums[i][current_speaker][prev_speaker] +=  sim #model.similarity(self.embeddings[self.length-i-1], embedding)
          self.window_lagged_contributions[i][current_speaker][prev_speaker] += 1
      if len(self.prev_window_speakers) >= self.tau_window:
        self.prev_window_speakers.pop(0)

      with np.errstate(divide='ignore', invalid='ignore'):
          cross_cohesion = np.divide(self.xi_sums, self.window_lagged_contributions)
          cross_cohesion = np.nan_to_num(cross_cohesion)

      return cross_cohesion

    # -------------------------------
    # Helper: normalize vector safely
    # -------------------------------
    def safe_normalize(self,v):
      v = np.asarray(v, dtype=np.float32)
      norm = np.linalg.norm(v)
      if norm > 0:
          v = v / norm
      return v.astype(np.float32)

    def aggregate_embeddings(self,embs, weighted=True):
      embs = np.asarray(embs, dtype=np.float32)

      if len(embs) == 0:
          return None

      if weighted and len(embs) > 1:
          weights = np.arange(1, len(embs) + 1, dtype=np.float32)
          weights = weights / weights.sum()
          agg = np.average(embs, axis=0, weights=weights)
      else:
          agg = np.mean(embs, axis=0)

      return self.safe_normalize(agg)
    
    # --------------------------------------------------
    # 1. Group-level past context for cross-speaker scores
    # --------------------------------------------------
    def group_level_past_context(self,min_lag,use_weighted_past ):
      group_contexts = []
      for i in range(min_lag):
          lag = i + 1
          context_window = self.embeddings[-lag:]
          context_embedding = self.aggregate_embeddings(context_window,weighted=use_weighted_past)
          group_contexts.append(context_embedding)
      return group_contexts
  
      # past_window = self.embeddings[-min_lag:]
      # group_past_context_embedding = self.aggregate_embeddings(past_window, weighted=use_weighted_past)

      # return group_past_context_embedding

    def speaker_cumulative_past_context_by_session(self, min_lag, use_weighted_past=True):
      """
      For each lag τ, identify the speaker who contributed at t-τ and aggregate
      that speaker's own contributions from the beginning of the session up to
      and including t-τ.

      Important:
      - self.embeddings contains only past contributions when this is called.
      - index 0 in the returned list corresponds to lag 1.
      - tau moves backward: lag 1 = most recent previous contribution,
        lag 2 = second most recent previous contribution, etc.
      """

      speaker_contexts = []
      total_past = len(self.embeddings)

      for i in range(min_lag):
          lag = i + 1
          lagged_position = total_past - lag

          if lagged_position < 0:
              speaker_contexts.append(None)
              continue

          # Speaker index at t - tau
          tau_speaker = self.embedding_speakers[lagged_position]

          # Only use that speaker's contributions from the beginning
          # up to and including the contribution at t - tau.
          speaker_history = [
              emb
              for emb, spk in zip(
                  self.embeddings[:lagged_position + 1],
                  self.embedding_speakers[:lagged_position + 1]
              )
              if spk == tau_speaker
          ]

          context_embedding = self.aggregate_embeddings(
              speaker_history,
              weighted=use_weighted_past
          )

          speaker_contexts.append({
              "lag": lag,
              "speaker": tau_speaker,
              "context_embedding": context_embedding,
              "history_count": len(speaker_history),
              "lagged_position": lagged_position
          })

      return speaker_contexts


    def speaker_cumulative_past_context_by_tau(self, min_lag, use_weighted_past=True):
      """
      Builds lag-faithful, speaker-specific past contexts within the current
      trailing lag window.

      For each lag tau:
        - identify the speaker at t - tau
        - aggregate only that speaker's contributions within the current
          lag window, from the window start up to and including t - tau
      """

      speaker_contexts = []

      total_past = len(self.embeddings)
      window_start = total_past - min_lag

      for i in range(min_lag):
          lag = i + 1
          lagged_position = total_past - lag
          lagged_speaker = self.embedding_speakers[lagged_position]

          context_embeddings = [
              emb
              for emb, spk in zip(
                  self.embeddings[window_start:lagged_position + 1],
                  self.embedding_speakers[window_start:lagged_position + 1]
              )
              if spk == lagged_speaker
          ]

          speaker_contexts.append(
              self.aggregate_embeddings(
                  context_embeddings,
                  weighted=use_weighted_past
              )
          )

      return speaker_contexts

    # --------------------------------------------------
    # 2. Current speaker past  contribution
    #    Uses recent speaker speaker_window_size contributions + current contribution
    # --------------------------------------------------
    def current_speaker_contextualized_contribution(self,current_speaker,embedding,speaker_window_size=2):
      speaker_past_embeddings = [emb for emb, spk in zip(self.embeddings, self.embedding_speakers) if spk == current_speaker]
      recent_self = speaker_past_embeddings[-speaker_window_size:]

      if len(recent_self) > 0:
        context = np.concatenate(( np.asarray(recent_self),np.array([embedding])))
        return self.aggregate_embeddings(context, weighted=True)
      else:
         return self.safe_normalize(embedding).astype(np.float32)
    
    # --------------------------------------------------
    # 3. Speaker-specific past context for internal cohesion
    # --------------------------------------------------
    def speaker_context_internal_cohesion(self,current_speaker,max_lag,use_weighted_past):
    
      speaker_past_embeddings = [emb for emb, spk in zip(self.embeddings, self.embedding_speakers) if spk == current_speaker]

      speaker_contexts = []

      for i in range(max_lag):
          lag = i + 1

          if len(speaker_past_embeddings) >= lag:
              # Take the most recent `lag` same-speaker contributions
              context_window = speaker_past_embeddings[-lag:]
              context_embedding = self.aggregate_embeddings(context_window, weighted=use_weighted_past)
              speaker_contexts.append(context_embedding)
          else:
              speaker_contexts.append(None)

      return speaker_contexts

    def calculateCohesionSums_V2(self, speaker, embedding, model,current_window_size=3,use_weighted_past=True):
      try:
          current_speaker = speaker
          min_lag = min(self.length, self.tau_window)

          if min_lag == 0:
              return np.zeros(
                  (self.tau_window, self.participants, self.participants)
              )

          current_embedding = self.safe_normalize(embedding).astype(np.float32)

          # --------------------------------------------------
          # Compute lag-faithful speaker-context similarity
          # --------------------------------------------------
          speaker_past_contexts = self.speaker_cumulative_past_context_by_session(
              min_lag,
              use_weighted_past
          )

          # --------------------------------------------------
          # Attribute scores to speaker-pair matrix.
          # Off-diagonal cells estimate cross-speaker cohesion.
          # Diagonal cells estimate internal cohesion.
          # --------------------------------------------------
          for i in range(0, min_lag):
              tau_context = speaker_past_contexts[i]

              if tau_context is None:
                  continue

              prev_speaker = tau_context["speaker"]
              speaker_context = tau_context["context_embedding"]

              if speaker_context is None:
                  continue

              speaker_sim = float(model.similarity(
                  speaker_context.astype(np.float32),
                  current_embedding
              ))

              self.xi_sums[i][current_speaker][prev_speaker] += speaker_sim
              self.window_lagged_contributions[i][current_speaker][prev_speaker] += 1

          
          if len(self.prev_window_speakers) >= self.tau_window:
              self.prev_window_speakers.pop(0)

          with np.errstate(divide='ignore', invalid='ignore'):
              cross_cohesion = np.divide(
                  self.xi_sums,
                  self.window_lagged_contributions
              )
              cross_cohesion = np.nan_to_num(cross_cohesion)

          return cross_cohesion

      except Exception as e:
          error_str = traceback.format_exc()
          logging.info("threw exception {0}".format(error_str))


    def calculateCohesionSums_V3(self, speaker, embedding, model,current_window_size=3,use_weighted_past=True):
      try:
          current_speaker = speaker
          min_lag = min(self.length, self.tau_window)

          if min_lag == 0:
              return np.zeros(
                  (self.tau_window, self.participants, self.participants)
              )

          current_embedding = self.safe_normalize(embedding).astype(np.float32)

          # --------------------------------------------------
          # Compute lag-faithful speaker-context similarity
          # --------------------------------------------------
          speaker_past_contexts = self.speaker_cumulative_past_context_by_tau(
              min_lag,
              use_weighted_past
          )

          # --------------------------------------------------
          # Attribute scores to speaker-pair matrix.
          # Off-diagonal cells estimate cross-speaker cohesion.
          # Diagonal cells estimate internal cohesion.
          # --------------------------------------------------
          for i in range(0, min_lag):
              # tau_context = speaker_past_contexts[i]

              # if tau_context is None:
              #     continue

              # prev_speaker = tau_context["speaker"]
              # speaker_context = tau_context["context_embedding"]

              # if speaker_context is None:
              #     continue

              # speaker_sim = float(model.similarity(
              #     speaker_context.astype(np.float32),
              #     current_embedding
              # ))

              # self.xi_sums[i][current_speaker][prev_speaker] += speaker_sim
              # self.window_lagged_contributions[i][current_speaker][prev_speaker] += 1

            lag = i + 1
            prev_speaker = self.indicies[self.prev_window_speakers[-lag]]
            speaker_context = speaker_past_contexts[i]

            if speaker_context is None:
                continue

            sim = float(
                model.similarity(
                    speaker_context.astype(np.float32),
                    self.safe_normalize(embedding).astype(np.float32)
                )
            )

            self.xi_sums[i][current_speaker][prev_speaker] += sim
            self.window_lagged_contributions[i][current_speaker][prev_speaker] += 1

          if len(self.prev_window_speakers) >= self.tau_window:
              self.prev_window_speakers.pop(0)

          with np.errstate(divide='ignore', invalid='ignore'):
              cross_cohesion = np.divide(
                  self.xi_sums,
                  self.window_lagged_contributions
              )
              cross_cohesion = np.nan_to_num(cross_cohesion)

          return cross_cohesion

      except Exception as e:
          error_str = traceback.format_exc()
          logging.info("threw exception {0}".format(error_str))


    # def subspaceProjection(self, s, v):
    #     proj = 0
    #     for vector in s:
    #         proj += projection(vector, v)
    #     return proj

    def subspaceProjection(self, basis, vector, epsilon=1e-12):
      vector = np.asarray(vector, dtype=float).reshape(-1)
      projection_sum = np.zeros_like(vector)

      for basis_vector in basis:
          basis_vector = np.asarray(basis_vector,dtype=float).reshape(-1)

          denominator = np.dot( basis_vector,basis_vector)

          if denominator > epsilon:
              projection_sum += ( np.dot(vector, basis_vector) / denominator) * basis_vector

      return projection_sum


    def processResponsivity(self, cross_cohesion):
        min_lag = min(self.length, self.tau_window)
        with np.errstate(divide='ignore', invalid='ignore'):
          responsivity = np.divide(np.sum(cross_cohesion, axis=0), max(min_lag, 1))
          responsivity = np.nan_to_num(responsivity)
        
        self.internal_cohesion = np.diagonal(responsivity)
        # logging.info("internal cohesio is {0}".format(self.internal_cohesion))
        denom = max(self.participants - 1, 1)
        self.social_impact = np.divide(np.sum(responsivity, axis=0, where=self.ignore_diag), denom)
        self.overall_responsivity = np.divide(np.sum(responsivity, axis=1, where=self.ignore_diag), denom)

    def processResponsivity_v2(self, cross_cohesion):
      valid_counts = np.count_nonzero(self.window_lagged_contributions,axis=0)

      with np.errstate(divide='ignore', invalid='ignore'):
          responsivity = np.divide(np.sum(cross_cohesion, axis=0),valid_counts)
          responsivity = np.nan_to_num(responsivity)
      self.internal_cohesion = np.diagonal(responsivity)
      # logging.info("internal cohesio is {0}".format(self.internal_cohesion))
      denom = max(self.participants - 1, 1)
      self.social_impact = np.divide(np.sum(responsivity, axis=0, where=self.ignore_diag),denom)
      self.overall_responsivity = np.divide(np.sum(responsivity, axis=1, where=self.ignore_diag),denom)

    # def calculateNewness_by_particpant_contributions(self, embedding, speaker):
    #     self.embeddings = np.concatenate((self.embeddings, np.array([embedding])))
    #     given_data = self.subspaceProjection(self.subspace_basis, embedding)
    #     new_data = np.array([embedding - given_data])
    #     self.total_new[speaker] += np.linalg.norm(new_data)/(np.linalg.norm(given_data) + np.linalg.norm(new_data))
    #     normalized_new_data = normalizeVector(new_data)
    #     self.subspace_basis = np.concatenate((self.subspace_basis, normalized_new_data), axis = 0)
    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         self.newness = np.divide(self.total_new, self.contributions)
    #         self.newness = np.nan_to_num(self.newness)

    def calculateNewness_by_participant_contributions(self,embedding,speaker,epsilon=1e-10):
      embedding = np.asarray(embedding,dtype=float,).reshape(-1)

      # 1. Project the current contribution onto the semantic
      #    space spanned by all previous contributions.
      if self.subspace_basis.size == 0:
          given_data = np.zeros_like(embedding)
      else:
          given_data = self.subspaceProjection(self.subspace_basis,embedding)

      # 2. Extract the semantic component not represented
      #    by previous contributions.
      new_data = embedding - given_data

      # Re-orthogonalize to reduce floating-point drift.
      if self.subspace_basis.size > 0:
          new_data -= self.subspaceProjection(self.subspace_basis,new_data)

      given_norm = np.linalg.norm(given_data)
      new_norm = np.linalg.norm(new_data)
      denominator = given_norm + new_norm

      # 3. GCA contribution-level Newness.
      contribution_newness = (
          new_norm / denominator
          if denominator > epsilon
          else 0.0
      )

      self.total_new[speaker] += contribution_newness

      # 4. Expand the basis only when the contribution introduces
      #    a genuinely new semantic direction.
      relative_tolerance = epsilon * max(np.linalg.norm(embedding),1.0 )

      if new_norm > relative_tolerance:
          normalized_new_data = new_data / new_norm

          if self.subspace_basis.size == 0:
              self.subspace_basis = (
                  normalized_new_data.reshape(1, -1)
              )
          else:
              self.subspace_basis = np.vstack(
                  [
                      self.subspace_basis,
                      normalized_new_data,
                  ]
              )

  
      # 6. GCA participant-level Newness:
      #    mean contribution-level Newness.
      self.newness = np.divide(
          self.total_new,
          self.contributions,
          out=np.full(
              self.total_new.shape,
              np.nan,
              dtype=float,
          ),
          where=self.contributions > 0,
      )

      return contribution_newness

    def calculateNewness_by_group_contributions(self, embedding, speaker):
        self.embeddings = np.concatenate((self.embeddings, np.array([embedding])))
        given_data = self.subspaceProjection(self.subspace_basis, embedding)
        new_data = np.array([embedding - given_data])
        self.total_new[speaker] += np.linalg.norm(new_data)/(np.linalg.norm(given_data) + np.linalg.norm(new_data))
        normalized_new_data = normalizeVector(new_data)
        self.subspace_basis = np.concatenate((self.subspace_basis, normalized_new_data), axis = 0)
        total_group_newness = np.sum(self.total_new)
        # logging.info("total newness matrix {0}, sum: {1} ".format(self.total_new,total_group_newness))
        # logging.info("contribution matrix {0}, sum: {1} ".format(self.contributions,np.sum(self.contributions)))
        with np.errstate(divide='ignore', invalid='ignore'):
            self.newness = self.total_new/total_group_newness
            self.newness = np.nan_to_num(self.newness)
       
    def start(self):
        self.running = True
        self.asr_complete = False

    def stop(self):
        self.running = False
        self.asr_complete = True

    def append_contribution_history(self,embedding,speaker_index,speaker_id):
          embedding = np.asarray(embedding,dtype=np.float32).reshape(1, -1)
    
          if self.embeddings.size == 0:
              self.embeddings = embedding
          else:
              self.embeddings = np.concatenate(
                  [self.embeddings, embedding],
                  axis=0,
              )
    
          self.embedding_speakers.append(speaker_index)
          self.prev_window_speakers.append(speaker_id)
          self.length += 1
    
    def process_transcript(self, speaker_transcript_data,action="realtime_processing"):
      try:
        processing_timer = time.time()
        speaker_ids = list(self.speakers.keys())

        speaker = speaker_transcript_data['speaker_id']
        transcript = speaker_transcript_data['transcript']
        p_score = None
        ic_score = None
        or_score = None
        si_score = None
        n_score = None
        cd_score = None

        if not transcript or speaker == -1:
          p_score = np.array([])
          ic_score = np.array([])
          or_score = np.array([])
          si_score = np.array([])
          n_score = np.array([])
          cd_score = np.array([])
        else:
          index = self.indicies[speaker] #self.indicies[speaker] + 1 if speaker != -1 else 0
          self.contributions[index] += 1

          embedding = self.semantic_model.encode(transcript)

          if self.length > 0:
            cross_cohesion = self.calculateCohesionSums_V3(index, embedding, self.semantic_model) #self.calculateCohesionSums(index, embedding, self.semantic_model)
            self.processResponsivity_v2(cross_cohesion) #self.processResponsivity(cross_cohesion)

          else:
            pass
            # self.embeddings = np.array([embedding])
            # self.subspace_basis = normalizeVector(self.embeddings)
            # self.total_new[index] += 1

          self.calculateNewness_by_participant_contributions(embedding, index)
          # Append the current contribution only after all metrics
          # relative to the preceding discourse have been calculated.
          self.append_contribution_history(embedding=embedding,speaker_index=index,speaker_id=speaker)
          # self.length += 1
          self.prev_window_speakers.append(speaker)
          self.embedding_speakers.append(index)
          self.participation_scores = np.subtract(np.multiply(np.divide(self.contributions, self.length), self.participants), 1)

          p_score = self.participation_scores
          ic_score = self.internal_cohesion
          or_score = self.overall_responsivity
          si_score = self.social_impact
          n_score = np.nan_to_num(self.newness,nan=0.0, posinf=0.0,neginf=0.0).astype(float) #self.newness
          cd_score = self.communication_density

        if action == "speaker metric recomputation":
          processing_time =  time.time() - processing_timer
          # logging.info("all metric score at {0} is {1},{2},{3},{4},{5},{6} for {7}".format(speaker_transcript_data['start_time'],p_score.tolist(),ic_score.tolist(),or_score.tolist(),si_score.tolist(),n_score.tolist(),cd_score.tolist(), transcript)) 
          # success = None
          success = callbacks.post_recomputed_speaker_transcript_metrics(speaker_transcript_data,
                                                    speaker_ids,
                                                    p_score.tolist(),
                                                    ic_score.tolist(),
                                                    or_score.tolist(),
                                                    si_score.tolist(),
                                                    n_score.tolist(),
                                                    cd_score.tolist())
        else:
          processing_time =  time.time() - processing_timer
          # logging.info("all metric score at {0} is {1},{2},{3},{4},{5},{6} for {7}".format(speaker_transcript_data['start_time'],p_score.tolist(),ic_score.tolist(),or_score.tolist(),si_score.tolist(),n_score.tolist(),cd_score.tolist(), transcript))  
          success = callbacks.post_speaker_transcript_metrics(speaker_transcript_data,
                                                    speaker_ids,
                                                    p_score.tolist(),
                                                    ic_score.tolist(),
                                                    or_score.tolist(),
                                                    si_score.tolist(),
                                                    n_score.tolist(),
                                                    cd_score.tolist())

        if success:
          logging.info('[Speaker_Metrics]Processing posted successfully for client {0} (Processing time: {1}) @ {2}'.format(self.auth_key, processing_time, processing_timer))
        else:
          logging.warning('[Speaker_Metrics]Processing results FAILED to post for client {0} (Processing time: {1})'.format(self.auth_key, processing_time))

      except Exception as e:
          logging.error('[Speaker Metrics]Processing FAILED for client {0}: {1}'.format(self.auth_key, e))


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
                  processor.calculateNewness_by_participant_contributions(embedding, index)

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
