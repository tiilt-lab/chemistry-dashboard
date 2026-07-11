import os
import json
import time
import glob
import queue
import shutil
import logging
import callbacks
import enrollment_check
import threading
import weakref
import wave
import scipy.signal
import config as cf
import numpy as np
try:
    import moviepy.editor as mp  # moviepy 1.x
except ImportError:
    import moviepy as mp  # moviepy 2.x dropped the .editor module
from queue import Full, Empty
from recorder import WaveRecorder
from recorder import VidRecorder
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager
from audio_buffer import AudioBuffer
from processor import AudioProcessor
from datetime import datetime
from redis_helper import RedisSessions
from twisted.python import log
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from asr_connectors.factory import create_asr
from features_detector import features_detector
from keyword_detector import keyword_detector
from speaker_tagging import speaker_tagging
from speechbrain.inference import SpeakerRecognition
from sentence_transformers import SentenceTransformer

cm = ConnectionManager()
# Sentence embedder for participation/cohesion metrics, selectable via
# [processing] semantic_embedder (config.py). Default 'all-mpnet-base-v2' keeps
# the light, low-latency model on the live path and preserves comparability with
# historical metrics; set 'bge-large-en-v1.5' to match the post-hoc default.
_SEMANTIC_IDS = {
    "all-mpnet-base-v2": "all-mpnet-base-v2",
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
}
_semantic_choice = cf.semantic_embedder()
semantic_model = SentenceTransformer(_SEMANTIC_IDS.get(_semantic_choice, _semantic_choice))
diarization_model = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/pretrained_ecapa")
semantic_model.share_memory()

class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = None
        self.running = False
        self.audio_buffer = None
        self.asr_audio_queue = None
        self.asr_transcript_queue = None
        self.asr = None
        self.processor = None
        self.last_message = time.time()
        self.end_signaled = False
        self.interval = 10
        self.awaitingSpeakers = True
        self.speakers = None
        self.currSpeaker = None
        self.currStudent = None
        self.currAlias = None
        # Escape hatch: after repeated quality-gate failures the client can
        # ask for the recording to be accepted anyway (verdict still logged).
        self.fingerprint_force = False

        logging.info('Loaded Diarization Model and Semantic Model...')

        cm.add(self)
        logging.info('New client connected...')

    def onMessage(self, payload, is_binary):
        self.last_message = time.time()
        if is_binary:
            try:
                self.process_binary(payload)
            except Exception as e:
                logging.warning('Error processing binary: {0}'.format(e))
        else:
            valid_json = False
            try:
                payload = payload.decode('utf-8')
                data = json.loads(payload)
                valid_json = True
            except Exception as e:
                logging.warning('Payload is not properly formatted JSON.')
                self.send_json({'type': 'error', 'message': 'Payload is not properly formatted JSON.'})
            if valid_json:
                try:
                    self.process_json(data)
                except Exception as e:
                    logging.warning('Error processing json: {0}'.format(e))

    def onClose(self, wasClean, code, reason):
        logging.info("close was trigered externally..... wasclean {0}, code {1}, reason {2}".format( wasClean, code, reason))
        self.signal_end()

    def process_json(self, data):
        if not 'type' in data:
            logging.warning('Message does not contain "type".')
            return
        if data['type'] == 'speaker':
            # Speakers can be added after the session starts, in which case
            # the start message carried numSpeakers=0 and self.speakers was
            # never initialized.
            if self.speakers is None:
                self.speakers = dict()
            if data['id'] == "done":
                self.awaitingSpeakers = False
                for speaker in data['speakers']:
                    self.speakers[speaker["id"]]["alias"] = speaker["alias"]
                self.processor.setSpeakerFingerprints(self.speakers)
                logging.info("Done awaiting all speakers info")
            else:
                self.currSpeaker = data['id']
                self.currAlias = data['alias']
                logging.info("preparing for speaker {}'s fingerprint".format(self.currSpeaker))
        
        if data['type'] == 'save-audio-video-fingerprinting':
            self.currStudent = data['id']
            self.stream_data  = data['streamdata']
            self.mediaExt = data['mimeextension']
            self.currAlias = data['alias']
            if self.stream_data == 'audio-video-fingerprint':
                self.video_file = os.path.join(cf.video_recordings_folder(), "{0}".format(self.currAlias))
                self.vid_recorder = VidRecorder(self.video_file,16000, 2, 1,self.mediaExt)
                    
            logging.info('save-audio-video-fingerprinting: Audio process connected')
            self.send_json({'type':'saveaudiovideo'})

        if data['type'] == 'fingerprint-force':
            self.fingerprint_force = True
            logging.info('fingerprint quality gate disabled for %s after repeated failures', self.currAlias)

        if data['type'] == 'add-saved-fingerprint':
            currSpeaker = data['id']
            currAlias = data['alias']
            # Any failure must reach the client, otherwise the join dialog
            # waits forever for registeredfingerprintadded.
            try:
                audio_fingerprint_file = os.path.join(cf.biometric_folder(), "{0}".format(currAlias))
                wavObj = wave.open(audio_fingerprint_file+'.wav')
                byte_audio_data = self.read_bytes_from_wav(wavObj)
                if currSpeaker and currAlias:
                    if self.speakers is None:
                        self.speakers = dict()
                    self.speakers[currSpeaker] = {"alias": currAlias, "data": byte_audio_data}
                    logging.info("storing registered speaker {}'s fingerprint with alias {}".format(currSpeaker, currAlias))
                    self.send_json({'type':'registeredfingerprintadded'})
                else:
                    logging.info("currentSpeaker and CurrentAlias are {0} {1}".format(currSpeaker,currAlias))
                    self.send_json({'type': 'registeredfingerprintfailed',
                                    'message': 'Missing speaker or username.'})
            except Exception as e:
                logging.warning('add-saved-fingerprint failed for alias %s: %s', currAlias, e)
                self.send_json({'type': 'registeredfingerprintfailed',
                                'message': 'No saved voice fingerprint found for this username.'})

        if data['type'] == 'heartbeat':
            auth_key = data.get('key', None)
            logging.info("Recieved Heartbeat from client with authkey {0}".format(auth_key))

        if data['type'] == 'start':
            valid, result = ProcessingConfig.from_json(data)
            logging.info(valid)
            if not valid:
                self.send_json({'type': 'error', 'message': result})
                self.signal_end()
            else:
                self.config = result
                cm.associate_keys(self, self.config.session_key, self.config.auth_key)
                self.stream_data = data['streamdata']
                logging.info(" numSpeakers is {}".format(data['numSpeakers'])) 
                if(data['numSpeakers'] != 0):
                    self.speakers = dict()
                    logging.info(" speaeker object was set  {}".format(self.speakers )) 

                if self.stream_data == 'audio':
                    if cf.record_original():
                        filename = os.path.join(cf.recordings_folder(), "{0} ({1})_orig".format(self.config.auth_key, str(time.ctime())))
                        self.orig_recorder = WaveRecorder(filename, self.config.sample_rate, self.config.depth, self.config.channels)
                    if cf.record_reduced():
                        filename = os.path.join(cf.recordings_folder(), "{0} ({1})_redu".format(self.config.auth_key, str(time.ctime())))
                        self.redu_recorder = WaveRecorder(filename, 16000, 2, 1)
                self.signal_start()
                self.send_json({'type':'start'})
                logging.info('Audio process connected')
                callbacks.post_connect(self.config.auth_key)

    def getRunning(self):
        return self.running

    def process_binary(self, data):
        if self.running and not self.awaitingSpeakers:
            if self.stream_data == 'audio':
                if cf.record_original():
                    # Save audio data.
                    self.orig_recorder.write(data)
                # Convert all audio to pcm_i16le
                data = self.reformat_data(data)
                data = self.resample_data(data)
                self.audio_buffer.append(data)
                asr_data = self.reduce_channels(1, data)
                # self.asr_audio_queue.put(asr_data)
                self.enqueue_latest_audio_chunk(asr_data)
                # Save audio data.
                if cf.record_reduced():
                    self.redu_recorder.write(asr_data)
    
        elif self.running and self.awaitingSpeakers:
            if self.currSpeaker:
                new_data = self.reformat_data(data)
                self.speakers[self.currSpeaker] = {"alias": self.currAlias, "data": new_data}
                logging.info("storing speaker {}'s fingerprint with alias {}".format(self.currSpeaker, self.currAlias))
                self.currSpeaker = None
                self.currAlias = None
        elif self.stream_data == 'audio-video-fingerprint':
            # Any failure in here must reach the client — an unhandled
            # exception used to bubble to onMessage's catch-all and the
            # sign-up page waited on "Processing…" forever.
            try:
                self.process_fingerprint_blob(data)
            except Exception as e:
                logging.warning('fingerprint save failed: %s', e, exc_info=True)
                self.send_json({'type': 'error',
                                'message': 'Saving the recording failed on the server. Please try again.'})
        else:
            self.send_json({'type': 'error', 'message': 'Binary audio data sent before start message.'})

    # A continuation take within this window is APPENDED to the student's
    # kept partial audio instead of starting the speech count from scratch.
    PARTIAL_MAX_AGE_SECONDS = 60 * 60

    def _append_wavs(self, first_path, second_path, out_path):
        # Both are 16k mono pcm16 written by our own extraction.
        import wave as _wave
        with _wave.open(first_path, 'rb') as a:
            params = a.getparams()
            frames = a.readframes(a.getnframes())
        with _wave.open(second_path, 'rb') as b:
            frames += b.readframes(b.getnframes())
        with _wave.open(out_path, 'wb') as out:
            out.setparams(params)
            out.writeframes(frames)

    def process_fingerprint_blob(self, data):
            self.vid_recorder.write(data)
            err = ""
            src = self.video_file+'.'+self.mediaExt
            if not os.path.isfile(src):
                raise RuntimeError('recording scratch file was not written: {0}'.format(src))
            audio_fingerprint_file = os.path.join(cf.biometric_folder(), "{0}.{1}".format(self.currAlias,"wav"))

            with mp.VideoFileClip(src, audio=True) as clip:
                # Keep the subclip within the media duration. Cap at 60s (the
                # RecordingCoach max), NOT self.interval — that 10s cap is the
                # live-ASR chunk size and used to silently truncate every
                # coached enrollment to its first ten seconds.
                end = min(60.0, float(clip.duration or 0))
                if end <= 0:
                    err = "Clip has zero/unknown duration"
                else:
                    sub = (clip.subclipped if hasattr(clip, 'subclipped') else clip.subclip)(0, end)  # moviepy 2 rename
                    if sub.audio is not None:
                        sub.audio.write_audiofile(
                                        audio_fingerprint_file ,
                                        fps=16000,
                                        nbytes=2,
                                        codec="pcm_s16le",
                                        ffmpeg_params=["-ac", "1", "-af", "aresample=resampler=soxr:precision=33"])
                    else:
                        # Fallback: there’s no audio track
                        err = "No audio stream"
            
            if os.path.isfile(src):
                os.remove(src)

            if err!="":
                self.send_json({'type': 'error', 'message': err})
            else:
                base = os.path.splitext(audio_fingerprint_file)[0]
                partial = base + '.partial.wav'
                # Cumulative takes: prepend a recent kept partial so the
                # student only needs to ADD speech, never restart from zero.
                try:
                    if os.path.isfile(partial):
                        if time.time() - os.path.getmtime(partial) <= self.PARTIAL_MAX_AGE_SECONDS:
                            combined = base + '.combined.tmp.wav'
                            self._append_wavs(partial, audio_fingerprint_file, combined)
                            os.replace(combined, audio_fingerprint_file)
                            logging.info('enrollment: appended new take to kept partial for %s', self.currAlias)
                        else:
                            os.remove(partial)
                except Exception as e:
                    logging.warning('enrollment partial merge failed (using new take only): %s', e)

                # Quality gate: enough cumulative speech + the recording must
                # match itself. Similarity to other students no longer blocks
                # (it is recorded in the verdict instead). Checker crashes
                # never block enrollment.
                verdict = None
                try:
                    verdict = enrollment_check.check_enrollment(
                        audio_fingerprint_file, self.currAlias, diarization_model)
                except Exception as e:
                    logging.warning('enrollment quality check failed to run: {0}'.format(e))
                if verdict is not None and not verdict['ok'] and not self.fingerprint_force:
                    # Keep the audio as the partial when the ONLY problem is
                    # not enough speech yet — the next take appends to it. A
                    # self-consistency failure means bad audio: start over.
                    insufficient = (verdict.get('still_needed_seconds') or 0) > 0
                    self_bad = (verdict.get('self_similarity') is not None
                                and verdict['self_similarity'] < enrollment_check.MIN_SELF_SIMILARITY)
                    keep_partial = insufficient and not self_bad
                    if keep_partial:
                        os.replace(audio_fingerprint_file, partial)
                    for p in (audio_fingerprint_file, base + '.emb.npy', base + '.check.json'):
                        if os.path.isfile(p):
                            os.remove(p)
                    if not keep_partial and os.path.isfile(partial):
                        os.remove(partial)
                    detail = dict(verdict)
                    detail['partial_kept'] = keep_partial
                    self.send_json({'type': 'quality_failed',
                                    'message': verdict['message'],
                                    'detail': detail})
                else:
                    if os.path.isfile(partial):
                        os.remove(partial)
                    logging.info('Audio biometrics saved')
                    self.send_json({'type': 'saved',
                                    'message': "Biometric data captured successfully",
                                    'quality': verdict})

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)

    # Changes the bit depth and encoding type.
    def reformat_data(self, in_data):
        if self.config.encoding == 'pcm_f32le':
            out_data = np.frombuffer(in_data, np.float32, -1)
            return (out_data * 32767.0).astype(np.int16, copy=False).tobytes()
        else:
            return in_data

    # Resampling leads to clicking in the output audio (scipy.signal.resample)
    def resample_data(self, in_data):
        if self.config.sample_rate != 16000:
            out_data = np.frombuffer(in_data, np.int16, -1)
            secs = len(out_data) / self.config.sample_rate
            samps = int(secs * 16000)
            return scipy.signal.resample(out_data, samps).astype(np.int16, copy=False).tobytes()
        else:
            return in_data

    # Reduces number of channels down to the desired amount.
    def reduce_channels(self, channels_wanted, in_data):
        if channels_wanted < self.config.channels:
            out_data = np.frombuffer(in_data, np.int16, -1)
            return out_data[channels_wanted::self.config.channels].tobytes()
        else:
            return in_data

    def read_bytes_from_wav(self,wav):
        wav.setpos(0)
        sdata = wav.readframes(wav.getnframes())
        data = np.frombuffer(sdata,dtype=np.dtype('int16'))
        return data.tobytes()

    def reduce_wav_channel(self,channels_wanted,wav):
        if channels_wanted < self.config.channels:
            nch = wav.getnchannels()
            wav.setpos(0)
            sdata = wav.readframes(wav.getnframes())
            data = np.frombuffer(sdata,dtype=np.dtype('int16'))
            ch_data = data[0::nch]
            return ch_data.tobytes()
        else:
            return self.read_bytes_from_wav(wav)

    def enqueue_latest_audio_chunk(self, asr_data, timeout=0.05):
        """
        Keep only the most recent chunk in the queue.
        If the queue is full, remove the stale queued chunk and replace it.
        """
        try:
            self.asr_audio_queue.put(asr_data, timeout=timeout)
            return True
        except Full:
            pass

        # Queue is full: drop the old queued item
        try:
            old_item = self.asr_audio_queue.get_nowait()
            # optional: if you use task_done semantics elsewhere, call task_done here
            # self.asr_audio_queue.task_done()
        except Empty:
            old_item = None

        # Try again to insert the latest chunk
        try:
            self.asr_audio_queue.put_nowait(asr_data)
            logging.debug("Replaced stale ASR audio chunk with latest chunk.")
            return True
        except Full:
            logging.warning("Could not enqueue latest ASR audio chunk; dropping it.")
            return False

    def signal_start(self):
        self.audio_buffer = AudioBuffer(self.config)
        self.asr_audio_queue = queue.Queue(maxsize=3)
        self.asr_transcript_queue = queue.Queue()
        self.asr = create_asr(cf.asr(), self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data, self.interval)
        self.asr.start()
        self.processor = AudioProcessor(self.audio_buffer, self.asr_transcript_queue, diarization_model, semantic_model, self.config)
        self.processor.start()
        self.running = True

    def send_close(self, message):
        self.send_json({'type': 'end', 'message': message})

    def signal_end(self):
        if self.end_signaled:
            return
        self.end_signaled = True
        if self.asr:
            self.asr.stop()
        if self.processor:
            self.processor.stop()

        if self.config:
            callbacks.post_disconnect(self.config.auth_key)
            cm.remove(self, self.config.session_key, self.config.auth_key)

       
        else:
            cm.remove(self, None, None)
        logging.info('Closing client connection...')
        self.transport.loseConnection()

        # Begin Post Processing
        if cf.record_reduced():
            self.redu_recorder.close()
        # if self.stream_data == 'video':
        #     self.orig_vid_recorder.close()
        if cf.record_original():
            self.orig_recorder.close()
            '''
            if self.config.tag:
                logging.info('Performing speaker tagging...')
                tagging_results = speaker_tagging.speaker_tagging(self.orig_recorder.wav_filename)
                taggings_posted = callbacks.post_tagging(self.config.auth_key, tagging_results)

                if taggings_posted:
                    logging.info('Processing results posted successfully for tagging {0} '.format(self.config.auth_key))
                else:
                    logging.info('Processing results FAILED to post for {0} '.format(self.config.auth_key))
            '''

if __name__ == '__main__':
    cf.initialize()

    # Initialize Logger
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

    # Run Server
    logging.info('Starting Audio Processing Service...')
    from features_detector.scorer_factory import get_scorer
    get_scorer(cf.scorer()).initialize()
    keyword_detector.initialize(cf.keyword_model_limit())

    poll_connections = task.LoopingCall(cm.check_connections)
    poll_connections.start(10.0)
    auth_connections = task.LoopingCall(cm.check_connection_authentication)
    auth_connections.start(5.0)
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol

    reactor.listenTCP(int(os.environ.get('DC_AUDIO_WS_PORT', 9000)), factory)
    logging.info('Audio Processing Service started.')
    reactor.run()
    logging.info('Audio Processing Service ended.')
