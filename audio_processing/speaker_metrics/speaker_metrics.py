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
          logging.info("simillarity is {0} for lag {1}".format(sim,lag))
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

    def calculateCohesionSums_V2(self,speaker,embedding,model,current_window_size=3,use_weighted_past=True):
      try:
        current_speaker = speaker
        min_lag = min(self.length, self.tau_window)
        if min_lag == 0:
          return np.zeros((self.tau_window, self.participants, self.participants))
      
      
        # --------------------------------------------------
        # 4. Compute group-context similarity
        # --------------------------------------------------
        group_past_context_embedding = self.group_level_past_context(min_lag,use_weighted_past)
        current_context_embedding = self.current_speaker_contextualized_contribution(current_window_size,embedding)
        # group_sim = model.similarity(group_past_context_embedding.astype(np.float32),current_context_embedding.astype(np.float32))
        # group_sim = float(group_sim)

        # --------------------------------------------------
        # 5. Compute internal speaker cohesion similarity
        # --------------------------------------------------
        speaker_past_context_embedding = self.speaker_context_internal_cohesion(current_speaker,min_lag,use_weighted_past)
      
        # logging.info("group cohesion sim={0}, internal speaker cohesion sim={1}, speaker={2}".format(group_sim,internal_sim,current_speaker))

        # --------------------------------------------------
        # 6. Attribute scores to speaker-pair matrix
        # --------------------------------------------------
        for i in range(0, min_lag):
          lag = i + 1
          prev_speaker = self.indicies[self.prev_window_speakers[-lag]]
          group_sim = float(model.similarity(group_past_context_embedding[i].astype(np.float32),self.safe_normalize(embedding).astype(np.float32))) #current_context_embedding.astype(np.float32)

          if prev_speaker != current_speaker:
              self.xi_sums[i][current_speaker][prev_speaker] += group_sim
              self.window_lagged_contributions[i][current_speaker][prev_speaker] += 1

          speaker_context = speaker_past_context_embedding[i]

          if speaker_context is not None:
              internal_sim = model.similarity(speaker_context.astype(np.float32),self.safe_normalize(embedding).astype(np.float32))
              internal_sim = float(internal_sim)

              self.xi_sums[i][current_speaker][current_speaker] += internal_sim
              self.window_lagged_contributions[i][current_speaker][current_speaker] += 1

        if len(self.prev_window_speakers) >= self.tau_window:
            self.prev_window_speakers.pop(0)

        with np.errstate(divide='ignore', invalid='ignore'):
            cross_cohesion = np.divide(
                self.xi_sums,
                self.window_lagged_contributions
            )
            cross_cohesion = np.nan_to_num(cross_cohesion)
        # logging.info("cross cohesion is {0}".format(cross_cohesion))
        return cross_cohesion
      except Exception as e:
        error_str = traceback.format_exc()
        logging.info("threw exception {0}".format(error_str))



    def subspaceProjection(self, s, v):
        proj = 0
        for vector in s:
            proj += projection(vector, v)
        return proj

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

    def calculateNewness_by_particpant_contributions(self, embedding, speaker):
        self.embeddings = np.concatenate((self.embeddings, np.array([embedding])))
        given_data = self.subspaceProjection(self.subspace_basis, embedding)
        new_data = np.array([embedding - given_data])
        self.total_new[speaker] += np.linalg.norm(new_data)/(np.linalg.norm(given_data) + np.linalg.norm(new_data))
        normalized_new_data = normalizeVector(new_data)
        self.subspace_basis = np.concatenate((self.subspace_basis, normalized_new_data), axis = 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            self.newness = np.divide(self.total_new, self.contributions)
            self.newness = np.nan_to_num(self.newness)

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
            cross_cohesion = self.calculateCohesionSums_V2(index, embedding, self.semantic_model) #self.calculateCohesionSums(index, embedding, self.semantic_model)
            self.processResponsivity_v2(cross_cohesion) #self.processResponsivity(cross_cohesion)
            self.calculateNewness_by_group_contributions(embedding, index)

          else:
            self.embeddings = np.array([embedding])
            self.subspace_basis = normalizeVector(self.embeddings)
            self.total_new[index] += 1

          self.length += 1
          self.prev_window_speakers.append(speaker)
          self.embedding_speakers.append(index)
          self.participation_scores = np.subtract(np.multiply(np.divide(self.contributions, self.length), self.participants), 1)

          p_score = self.participation_scores
          ic_score = self.internal_cohesion
          or_score = self.overall_responsivity
          si_score = self.social_impact
          n_score = self.newness
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
                  processor.calculateNewness_by_particpant_contributions(embedding, index)

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
