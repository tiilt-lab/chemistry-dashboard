import soundfile as sf
import traceback
import threading
import logging
import numpy as np
import time
import json
from queue import Full

class AudioStreamReader:
    def __init__(self, audio_buffer, asr_audio_queue,audio_file,queue_put_timeout, config,STOP_SIGNAL,running_audio_processes, realtime=True):
        # realtime=True paces the file at 1x speed — required only by the
        # streaming Google ASR. Batch ASRs (WhisperX/Qwen3) read the whole
        # buffer up front, so pacing just adds the recording's full duration
        # to every re-run for no benefit.
        self.realtime = realtime
        self.audio_buffer = audio_buffer
        self.asr_audio_queue = asr_audio_queue
        self.config = config
        self.audio_file = audio_file
        self.queue_put_timeout = queue_put_timeout
        self.STOP_SIGNAL = STOP_SIGNAL
        self.running = True
        self.running_audio_processes = running_audio_processes

    def add_websocket_connection(self,web_socket):
        self.web_socket_connection = web_socket


    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.web_socket_connection.sendMessage(payload, isBinary = False)

    def start(self):
        self.processing_thread = threading.Thread(target=self._run,name="audio_stream_reader")
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop(self):
        self.running = False

    def _run(self, extra_lag=0.0):
        try:
            audio, sample_rate = sf.read(self.audio_file, dtype="float32")
            # # Convert stereo to mono if needed
            # if audio.ndim > 1:
            #     audio = audio.mean(axis=1)

            audio = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio * 32767).astype(np.int16)
            
            if sample_rate != 16000:
                raise ValueError(f"Expected 16000 Hz, got {sample_rate}")
    
            chunk_size = 4096
            chunk_duration = chunk_size / sample_rate

            for i in range(0, len(audio_int16), chunk_size):
                chunk = audio_int16[i:i + chunk_size]
                if chunk.size == 0:
                    continue

                chunk_bytes = chunk.tobytes()
                if len(chunk_bytes) == 0:
                    continue    

                self.audio_buffer.append(chunk_bytes)
                self.asr_audio_queue.put(chunk_bytes, timeout=self.queue_put_timeout)
                
                if self.running == False:
                    break
                
                if self.realtime:
                    time.sleep(chunk_duration)
              
        except Exception as e:
            error_str = traceback.format_exc()
            logging.info('exception occured while reading wav : {0}'.format(error_str))
        finally:
            try:
                self.asr_audio_queue.put(self.STOP_SIGNAL, timeout=self.queue_put_timeout)
                logging.info('Audio Stream Reader thread stopped for {0}.'.format(self.config.auth_key))
                # Completion is signalled by the processor when all utterances
                # are done - the reader finishing only means the file was read.
            except Full:
                pass

    
       
