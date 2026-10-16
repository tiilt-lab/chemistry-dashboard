import os
import time
import queue
import threading
import logging
import callbacks
import enrollment_check
import enrollment_media
import wave
import config as cf
from queue import Full, Empty
from recorder import WaveRecorder
from recorder import VidRecorder
from processing_config import ProcessingConfig
from connection_manager import ConnectionManager  # also puts src/common on sys.path
import os as _rs_os, sys as _rs_sys  # noqa: E401
_rs_c = _rs_os.path.dirname(_rs_os.path.abspath(__file__))
while _rs_c != '/' and not _rs_os.path.isdir(_rs_os.path.join(_rs_c, 'common')):
    _rs_c = _rs_os.path.dirname(_rs_c)
_rs_c = _rs_os.path.join(_rs_c, 'common')
if _rs_c not in _rs_sys.path:
    _rs_sys.path.insert(0, _rs_c)
import reactor_safety  # reactor/thread boundary; src/common bootstrapped above
from ws_protocol import WsMessageMixin  # shared onMessage/onClose
import audio_bytes
import safe_names
import redis_client  # shared lazy client (src/common); enrollment tokens live beside the session keys
from enrollment_token import enrollment_allows
import live_presence  # live_pod:<key> keys the post-hoc services defer to (src/common)
import clock_anchor  # the pod's clock on the session timeline, anchored to the audio actually received
import recording_sidecar  # <recording>.clock.json: how the recording's samples map to the session clock
import timeline_recorder  # one track per pod on the session clock, across reconnects (stamped frames)
import struct
from audio_buffer import AudioBuffer
import asr_ingest  # reactor-side ingest bookkeeping (stamped chunks, drop counter)
import live_metrics  # Prometheus exporter accessors (src/common/blinc_metrics)
import segment_pool  # process-wide bounded utterance pool; drained at exit
from ecapa_device import load_ecapa
from processor import AudioProcessor
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from asr_connectors.factory import create_asr
from keyword_detector import keyword_detector
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
# ECAPA on CUDA when it is there and has >= 1.5 GB free, else CPU (audit
# B.4). Every consumer (.emb.npy cache, enrollment check, live matching)
# already moves embeddings to host memory, so the device is transparent.
diarization_model, _ecapa_device = load_ecapa(
    SpeakerRecognition.from_hparams,
    source="speechbrain/spkrec-ecapa-voxceleb", savedir="pretrained_models/pretrained_ecapa")
semantic_model.share_memory()

class ServerProtocol(WsMessageMixin, WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = None
        self.running = False
        self.audio_buffer = None
        self.asr_audio_queue = None
        self.asr_transcript_queue = None
        self._ingest = None
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
        # Serializes deferred enrollment-blob processing for this connection.
        self._fingerprint_lock = threading.Lock()
        # LoopingCall refreshing this pod's live_pod:<key> presence.
        self._presence = None
        self.clock = None
        self.recording_paths = []
        self.timeline = None
        self._held = []          # stamped frames that arrived before the stream was ready
        self._held_bytes = 0
        # Last asr_status state sent to this pod (read by live_metrics).
        self.asr_state = 'ok'

        logging.info('Loaded Diarization Model and Semantic Model...')

        cm.add(self)
        logging.info('New client connected...')

    # onMessage / onClose come from WsMessageMixin (shared across both services).

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
                    entry = self.speakers.get(speaker["id"])
                    if entry is None:
                        # Client re-validated after a reconnect without
                        # re-sending this speaker's fingerprint; don't crash
                        # the whole message on the missing entry.
                        logging.warning('speaker %s validated with no fingerprint on this connection', speaker["id"])
                        continue
                    entry["alias"] = speaker["alias"]
                self.processor.setSpeakerFingerprints(self.speakers)
                logging.info("Done awaiting all speakers info")
                self._flush_held_frames()
            else:
                self.currSpeaker = data['id']
                self.currAlias = data['alias']
                logging.info("preparing for speaker {}'s fingerprint".format(self.currSpeaker))
        
        if data['type'] == 'save-audio-video-fingerprinting':
            # Gate first: this socket is public and a passing enrollment
            # replaces (or, on a failed quality gate, deletes) the alias's
            # voice print. Nothing is stored -- so no binary is accepted --
            # until the token /addstudent minted for THIS alias checks out.
            if not enrollment_allows(redis_client._redis(), data.get('token'), data.get('alias')):
                logging.warning('rejected fingerprint enrollment: bad token for alias %r', data.get('alias'))
                self.send_json({'type': 'error', 'message': 'Enrollment not authorised. Start again from the sign-up page.'})
                return
            self.currStudent = data['id']
            self.stream_data  = data['streamdata']
            # alias/extension come straight off the socket and build file
            # paths — sanitize before any use, or reject the enrollment.
            try:
                self.currAlias = safe_names.safe_name(data['alias'])
            except safe_names.UnsafeName:
                logging.warning('rejected fingerprint enrollment: unsafe alias %r', data.get('alias'))
                self.send_json({'type': 'error', 'message': 'Invalid name.'})
                return
            self.mediaExt = safe_names.safe_media_ext(data['mimeextension'])
            # Voice-only enrollment (no camera): the take is an audio-only
            # container, opened as sound rather than video.
            self.voice_only = bool(data.get('voice_only'))
            if self.stream_data == 'audio-video-fingerprint':
                self.video_file = os.path.join(cf.video_recordings_folder(), "{0}".format(self.currAlias))
                self.vid_recorder = VidRecorder(self.video_file,16000, 2, 1,self.mediaExt)

            logging.info('save-audio-video-fingerprinting: Audio process connected%s', ' (voice only)' if self.voice_only else '')
            self.send_json({'type':'saveaudiovideo'})

        if data['type'] == 'fingerprint-force':
            # Only meaningful once an authorised enrollment is in progress on
            # this connection (stream_data is set after the token check).
            if getattr(self, 'stream_data', None) != 'audio-video-fingerprint':
                logging.warning('ignored fingerprint-force with no authorised enrollment in progress')
                return
            self.fingerprint_force = True
            logging.info('fingerprint quality gate disabled for %s after repeated failures', self.currAlias)

        if data['type'] == 'add-saved-fingerprint':
            currSpeaker = data['id']
            currAlias = data.get('alias')  # raw, for logging; validated below
            # Any failure must reach the client, otherwise the join dialog
            # waits forever for registeredfingerprintadded.
            try:
                currAlias = safe_names.safe_name(data['alias'])
                audio_fingerprint_file = os.path.join(cf.biometric_folder(), "{0}".format(currAlias))
                # The voice print (<alias>.emb.npy) is what matching uses;
                # the recording is only read where a legacy enrollment
                # still has nothing else.
                if os.path.isfile(audio_fingerprint_file + '.emb.npy'):
                    byte_audio_data = b''
                else:
                    with wave.open(audio_fingerprint_file+'.wav') as wavObj:
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
                        self.recording_paths.append(filename)
                    if cf.record_reduced():
                        filename = os.path.join(cf.recordings_folder(), "{0} ({1})_redu".format(self.config.auth_key, str(time.ctime())))
                        self.redu_recorder = WaveRecorder(filename, 16000, 2, 1)
                        self.recording_paths.append(filename)
                self.signal_start()
                self.send_json({'type':'start'})
                logging.info('Audio process connected')
                reactor_safety.defer_blocking(callbacks.post_connect, self.config.auth_key)

    def getRunning(self):
        return self.running

    def _raw_seconds(self, data):
        # Duration of a browser frame as sent (float32/int16 at the stream's
        # rate and channel count), for the clock's discard accounting.
        cfg = self.config
        if cfg is None or not cfg.sample_rate or not cfg.channels:
            return 0.0
        return len(data) / float(cfg.depth * cfg.sample_rate * cfg.channels)

    HELD_MAX_BYTES = 300 * 16000 * 4   # 300 s of 16 kHz float32: a whole pre-Start buffer

    def _split_stamp(self, data):
        # (capture time or None, samples): a client that said frame_timestamps
        # prefixes every worklet frame with its AudioContext time as a
        # little-endian float64 (audio-frame.js). NaN means an older worklet.
        cfg = self.config
        if cfg is not None and getattr(cfg, 'frame_timestamps', False) and len(data) >= 8:
            (t,) = struct.unpack('<d', bytes(data[:8]))
            return (t if t == t else None), data[8:]
        return None, data

    def _hold_frame(self, stamp, payload):
        # The stream is not ready (speaker fingerprints still arriving); a
        # stamped frame loses nothing by waiting, it lands by its stamp.
        if self._held_bytes + len(payload) > self.HELD_MAX_BYTES:
            self.clock.discard(self._raw_seconds(payload))
            return
        self._held.append((stamp, bytes(payload)))
        self._held_bytes += len(payload)

    def _flush_held_frames(self):
        held, self._held, self._held_bytes = self._held, [], 0
        if held and self.running and not self.awaitingSpeakers and self.stream_data == 'audio':
            logging.info('%s: %d held frames placed by their stamps', self.config.auth_key, len(held))
            for stamp, payload in held:
                self._process_audio_frame(payload, stamp)

    def _process_audio_frame(self, data, stamp=None):
        if cf.record_original():
            # Save audio data.
            self.orig_recorder.write(data)
        # Convert all audio to pcm_i16le
        data = self.reformat_data(data)
        data = self.resample_data(data)
        counted_before = self._ingest.seconds(self._ingest.samples_received)
        self.audio_buffer.append(data)
        asr_data = self.reduce_channels(1, data)
        self.enqueue_latest_audio_chunk(asr_data)
        if stamp is not None and getattr(self.config, 'capture_origin', None) is not None:
            self._track_stamped(stamp, counted_before)
        else:
            self._track_clock()
        # Save audio data.
        if cf.record_reduced():
            self.redu_recorder.write(asr_data)
        if stamp is not None and self.timeline is not None and getattr(self.config, 'capture_origin', None) is not None:
            self.timeline.write(asr_data, self.config.capture_origin + stamp)

    def _track_stamped(self, stamp, counted_before):
        # A stamped frame says where it sits on the session clock; the sample
        # count says where the service would have put it. Any difference past
        # STAMP_SNAP moves the clock, at once and in either direction.
        if self.clock.first_frame_at is None:
            self.clock.first_frame_at = time.time()
        stamped = self.config.capture_origin + stamp
        counted = self.config.start_offset + counted_before
        delta = self.clock.stamped_frame(stamped, counted)
        if delta:
            self.config.start_offset += delta
            self._clock_moved(delta)
            log = logging.warning if abs(delta) >= 1.0 else logging.info
            log('%s: pod clock moved %+.2f s to the frame stamps', self.config.auth_key, delta)

    def process_binary(self, data):
        if self.stream_data == 'audio' and self.config is not None and not (self.running and self.awaitingSpeakers and self.currSpeaker):
            stamp, payload = self._split_stamp(data)
            if not self.running or self.awaitingSpeakers:
                # Audio arriving before the stream is ready (the speaker
                # fingerprints still awaited) used to vanish silently. A
                # stamped frame is held and placed by its stamp when the
                # stream is ready; an unstamped one is still dropped, but the
                # clock is moved forward by what it had promised and never
                # counted (clock_anchor.discard).
                if stamp is not None:
                    self._hold_frame(stamp, payload)
                elif self.clock is not None:
                    discarded = self.clock.discard(self._raw_seconds(payload))
                    if discarded:
                        self.config.start_offset += discarded
                        self._clock_moved(discarded)
                return
            self._process_audio_frame(payload, stamp)
            return
        if self.running and self.awaitingSpeakers:
            if self.currSpeaker:
                new_data = self.reformat_data(data)
                self.speakers[self.currSpeaker] = {"alias": self.currAlias, "data": new_data}
                logging.info("storing speaker {}'s fingerprint with alias {}".format(self.currSpeaker, self.currAlias))
                self.currSpeaker = None
                self.currAlias = None
        elif self.stream_data == 'audio-video-fingerprint':
            # Deferred off the reactor: this decodes up to 60s of video
            # (moviepy/ffmpeg), embeds it (ECAPA), and cross-matches against
            # every enrollment on disk — done inline it stalled captions and
            # heartbeats for EVERY connected pod for seconds per blob. Any
            # failure must still reach the client — an unhandled exception
            # used to leave the sign-up page on "Processing…" forever.

            def _work(blob=data):
                with self._fingerprint_lock:
                    self.process_fingerprint_blob(blob)

            def _fail(f):
                logging.warning('fingerprint save failed: %s', f.getErrorMessage(), exc_info=False)
                self.send_json({'type': 'error',
                                'message': 'Saving the recording failed on the server. Please try again.'})

            reactor_safety.defer_blocking(_work).addErrback(_fail)
        else:
            self.send_json({'type': 'error', 'message': 'Binary audio data sent before start message.'})

    # A continuation take within this window is APPENDED to the student's
    # kept partial audio instead of starting the speech count from scratch.
    PARTIAL_MAX_AGE_SECONDS = 60 * 60

    def _append_wavs(self, first_path, second_path, out_path):
        # Both are 16k mono pcm16 written by our own extraction.
        with wave.open(first_path, 'rb') as a:
            params = a.getparams()
            frames = a.readframes(a.getnframes())
        with wave.open(second_path, 'rb') as b:
            frames += b.readframes(b.getnframes())
        with wave.open(out_path, 'wb') as out:
            out.setparams(params)
            out.writeframes(frames)

    def process_fingerprint_blob(self, data):
            # Each incoming blob is a complete standalone recording, but the
            # scratch file is per-alias and VidRecorder appends. Without a
            # reset, a retake is appended after the previous take (ffmpeg then
            # re-reads take 1), and a truncated earlier upload leaves garbage
            # at byte 0 that makes ffmpeg reject every later attempt for that
            # alias forever. Start every blob on a fresh file.
            try:
                os.remove(self.video_file + '.' + self.mediaExt)
            except OSError:
                pass
            self.vid_recorder.write(data)
            err = ""
            src = self.video_file+'.'+self.mediaExt
            if not os.path.isfile(src):
                raise RuntimeError('recording scratch file was not written: {0}'.format(src))
            audio_fingerprint_file = os.path.join(cf.biometric_folder(), "{0}.{1}".format(self.currAlias,"wav"))

            # Capped at 60s (the RecordingCoach max), NOT self.interval: that
            # 10s cap is the live-ASR chunk size and used to silently
            # truncate every coached enrollment to its first ten seconds.
            err = enrollment_media.extract_audio(src, audio_fingerprint_file,
                                                 voice_only=getattr(self, 'voice_only', False))

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
                    # Only the voice print is kept: the recording goes as
                    # soon as its embedding is cached (every consumer reads
                    # <alias>.emb.npy; the WAV stays only if no print could
                    # be made, so an enrollment is never lost).
                    if enrollment_check.drop_wav_after_embedding(audio_fingerprint_file, diarization_model):
                        logging.info('Audio biometrics saved (voice print only)')
                    else:
                        logging.warning('Audio biometrics saved; recording kept because no voice print could be cached for %s', self.currAlias)
                    self.send_json({'type': 'saved',
                                    'message': "Biometric data captured successfully",
                                    'quality': verdict})

    def send_json(self, message):
        # The one sanctioned transport-write path (reactor-safe from worker
        # threads; best-effort on a dead socket). See common/reactor_safety.
        reactor_safety.send_json(self, message)

    # PCM helpers live in src/common/audio_bytes.py, shared with the other
    # three WS servers; these delegates keep the config-bound call shape.
    def reformat_data(self, in_data):
        return audio_bytes.reformat_data(in_data, self.config.encoding)

    def resample_data(self, in_data):
        return audio_bytes.resample_data(in_data, self.config.sample_rate)

    def reduce_channels(self, channels_wanted, in_data):
        return audio_bytes.reduce_channels(channels_wanted, in_data, self.config.channels)

    def read_bytes_from_wav(self,wav):
        return audio_bytes.read_bytes_from_wav(wav)

    def reduce_wav_channel(self,channels_wanted,wav):
        return audio_bytes.reduce_wav_channel(channels_wanted, wav, self.config.channels)

    def enqueue_latest_audio_chunk(self, asr_data):
        """Non-blocking hand-off to the ASR thread; runs on the reactor.

        Never waits: the old 50ms blocking put stalled every pod's ingest
        whenever one consumer lagged. The chunk carries its absolute sample
        offset (counted over everything received), so a drop shifts no later
        timestamp. When the queue is full the OLDEST chunk is evicted — the
        newest audio is worth more to live captions — and the loss is counted
        and reported at WARNING, at most every ~30s per pod.
        """
        chunk = asr_ingest.StampedChunk(asr_data, self._ingest.received(len(asr_data)))
        try:
            self.asr_audio_queue.put_nowait(chunk)
            return True
        except Full:
            pass
        lost = 0
        try:
            lost = len(self.asr_audio_queue.get_nowait())
        except Empty:
            pass
        try:
            self.asr_audio_queue.put_nowait(chunk)
        except Full:
            lost += len(chunk)
        if lost:
            warning = self._ingest.dropped(lost, time.time())
            if warning:
                logging.warning('%s: %s', self.config.auth_key, warning)
        return False

    def signal_start(self):
        self.audio_buffer = AudioBuffer(self.config)
        self._ingest = asr_ingest.IngestCounter()
        # start_offset was computed for this moment; the audio decides from
        # here (clock_anchor.py).
        self.clock = clock_anchor.ClockAnchor(time.time(), getattr(self.config, 'reported_backlog', 0.0))
        self.clock_moves = []
        self._write_clock_sidecars()
        # Stamped frames can be placed on the session clock exactly, so they
        # also go to the pod's single timeline track (timeline_recorder.py),
        # which a reconnect appends to.
        if getattr(self.config, 'frame_timestamps', False) and self.stream_data == 'audio' and cf.record_reduced():
            self.timeline = timeline_recorder.for_pod(cf.recordings_folder(), self.config.auth_key)
        self.asr_audio_queue = queue.Queue(maxsize=asr_ingest.QUEUE_CHUNKS)
        self.asr_transcript_queue = queue.Queue()
        # The session's locked-at-creation ASR choice wins; the deployment
        # config is the default for sessions that didn't choose.
        self.asr = create_asr(getattr(self.config, 'asr', None) or cf.asr(), self.asr_audio_queue, self.asr_transcript_queue, self.config, self.stream_data, self.interval)
        # Connectors with a shared worker report it degraded/ok; relay that
        # to this pod's client (fires on worker threads; send_json marshals
        # onto the reactor).
        if hasattr(self.asr, 'on_status'):
            self.asr.on_status = self._send_asr_status
        self.asr.start()
        self.processor = AudioProcessor(self.audio_buffer, self.asr_transcript_queue, diarization_model, semantic_model, self.config)
        self.processor.start()
        self.running = True
        self._start_presence()

    def _write_clock_sidecars(self):
        # Beside each recording of this connection: where sample 0 sits on
        # the session clock and every move made since, so the recording can
        # be placed on the session clock afterwards (recording_sidecar.py).
        if not self.recording_paths or self.config is None:
            return
        info = {'processing_key': self.config.auth_key, 'session_id': self.config.sessionId,
                'device_id': self.config.deviceId, 'start_offset': round(float(self.config.start_offset), 3),
                'reported_backlog': round(float(getattr(self.config, 'reported_backlog', 0.0) or 0.0), 3),
                'moves': list(self.clock_moves)}
        for base in self.recording_paths:
            try:
                recording_sidecar.write(base + '.wav', info)
            except Exception:
                logging.exception('%s: could not write the clock sidecar for %s', self.config.auth_key, base)

    def _clock_moved(self, delta):
        # A move is at the audio position where it took effect; the sidecar's
        # start_offset stays the value the first sample was stamped with.
        at = self._ingest.seconds(self._ingest.samples_received) if self._ingest is not None else 0.0
        self.clock_moves.append({'at': round(float(at), 3), 'delta': round(float(delta), 3)})
        self._write_clock_sidecars()

    def _track_clock(self):
        # The pod's clock (clock_anchor.py): stamps count the samples
        # received, so audio that begins late or stalls drifts from real
        # time. Reactor thread; start_offset is read by the processor thread
        # per utterance, so a move applies from the next transcript on.
        clock = self.clock
        if clock is None:
            return
        now = time.time()
        if clock.first_frame_at is None:
            late = clock.first_frame(now)
            if late:
                self.config.start_offset += late
                self._clock_moved(late)
                logging.info('%s: audio began %.1f s after the start message; clock anchored to the first frame',
                             self.config.auth_key, late)
            return
        delta = clock.frame(self._ingest.seconds(self._ingest.samples_received), now)
        if delta:
            self.config.start_offset += delta
            self._clock_moved(delta)
            logging.warning('%s: pod clock moved %+.1f s (audio was running %.1f s %s real time)',
                            self.config.auth_key, delta, abs(delta), 'behind' if delta > 0 else 'ahead of')

    # Live presence (common/live_presence): while this pod streams, the
    # post-hoc services see live_pod:<processing_key> and defer GPU-heavy
    # jobs. Redis I/O runs off the reactor (a stalled Redis must not stall
    # ingest) and is best effort: the key's TTL covers a crashed process.
    # The pod's clock report rides along for the Devices tab.
    def _mark_live(self):
        key = self.config.auth_key
        clock = self.clock.snapshot() if self.clock is not None else None

        def _fail(f):
            logging.warning('live presence refresh failed for %s: %s', key, f.getErrorMessage())

        def _refresh():
            r = redis_client._redis()
            live_presence.mark_live(r, key)
            if clock is not None:
                live_presence.set_clock(r, key, clock)

        reactor_safety.defer_blocking(_refresh).addErrback(_fail)

    def _start_presence(self):
        self._presence = task.LoopingCall(self._mark_live)
        self._presence.start(live_presence.REFRESH_SECONDS, now=True)

    def _stop_presence(self):
        lc, self._presence = self._presence, None
        if lc is not None and lc.running:
            lc.stop()
        if lc is not None and self.config:
            key = self.config.auth_key

            def _fail(f):
                logging.warning('live presence clear failed for %s (TTL will expire it): %s',
                                key, f.getErrorMessage())

            def _clear():
                r = redis_client._redis()
                live_presence.clear_live(r, key)
                live_presence.clear_clock(r, key)

            reactor_safety.defer_blocking(_clear).addErrback(_fail)

    def send_close(self, message):
        self.send_json({'type': 'end', 'message': message})

    def _send_asr_status(self, state, message=None):
        # Browser contract: {"type": "asr_status", "state": "ok"|"degraded", "message"?: str}
        self.asr_state = state
        status = {'type': 'asr_status', 'state': state}
        if message:
            status['message'] = message
        self.send_json(status)

    def signal_end(self):
        if self.end_signaled:
            return
        self.end_signaled = True
        self._stop_presence()
        live_metrics.retire(self._ingest)  # keep the exported ingest totals monotonic
        if self.asr:
            self.asr.stop()
        if self.processor:
            self.processor.stop()

        if self.config:
            # 30s-timeout HTTP off the reactor; teardown must not stall ingest.
            reactor_safety.defer_blocking(callbacks.post_disconnect, self.config.auth_key)
            cm.remove(self, self.config.session_key, self.config.auth_key)

       
        else:
            cm.remove(self, None, None)
        logging.info('Closing client connection...')
        self.transport.loseConnection()

        # Begin Post Processing
        # The recorders only exist on live audio connections (created in
        # signal_start); fingerprint-enrollment connections close through
        # here too and used to throw AttributeError into the log every time.
        # Deferred off the reactor: close() converts the whole session .dat
        # to wav — done inline it stalled ingest for every connected pod for
        # the duration of the conversion. Nothing here consumes the .wav
        # synchronously (posthoc reads it much later).
        recorders = []
        if cf.record_reduced() and getattr(self, 'redu_recorder', None):
            recorders.append(self.redu_recorder)
        if self.timeline is not None and self.timeline.start is not None:
            # The timeline's samples sit on the session clock directly.
            self.timeline.finalize()
            try:
                recording_sidecar.write(self.timeline.wav, {
                    'processing_key': self.config.auth_key, 'session_id': self.config.sessionId,
                    'device_id': self.config.deviceId, 'start_offset': round(self.timeline.start, 3),
                    'timeline': True, 'moves': []})
            except Exception:
                logging.exception('%s: could not write the timeline sidecar', self.config.auth_key)
        if cf.record_original() and getattr(self, 'orig_recorder', None):
            recorders.append(self.orig_recorder)
        if recorders:

            def _close_all(recs=recorders):
                for r in recs:
                    r.close()

            reactor_safety.defer_blocking(_close_all)

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
    # Keepalive: a dead peer used to linger up to 300s (inactivity sweep)
    # holding its ASR threads. Payload cap: enrollment sends one ~60s webm
    # blob (3 Mbps video + 128 kbps audio, ~23.5 MB) as a single message;
    # live audio chunks are ~16 KB.
    factory.setProtocolOptions(autoPingInterval=10, autoPingTimeout=20,
                               maxMessagePayloadSize=64 * 1024 * 1024)
    factory.protocol = ServerProtocol

    reactor.listenTCP(int(os.environ.get('DC_AUDIO_WS_PORT', 9000)), factory)
    # Prometheus exporter (loopback, BLINC_METRICS_PORT, default 9111).
    live_metrics.install(cm, retry_queue=getattr(callbacks, '_RETRIES', None))
    logging.info('Audio Processing Service started.')
    reactor.run()
    # Non-daemon pool threads: cancel queued utterances so a backlog can't
    # hold the process past the reactor stop (in-flight ones finish).
    segment_pool.shutdown()
    logging.info('Audio Processing Service ended.')
