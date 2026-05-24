import asyncio
import websockets
import threading
from scipy.io import wavfile
import numpy as np
import wave
import ssl
import threading
import json
import time

class AudioProcessorClient:

    def __init__(self, url, https=False):
        self.running = False
        self.https = https
        self.url = '{0}://{1}/audio_socket'.format('wss' if https else 'ws', url)
        self.lock = threading.Lock()

    def start(self, audio_file, key):
        if self.running:
            return False
        self.audio = WaveParser(audio_file)
        self.running = True
        self.config = {
            'type':'start',
            'sample_rate': self.audio.sample_rate,
            'encoding': 'pcm_i16le' if self.audio.depth == 2 else 'pcm_f32le',
            'channels': self.audio.channels,
            'key': key,
            'tag': True
        }
        asyncio.get_event_loop().run_until_complete(self.transmit_audio())
        return True

    def stop(self):
        if self.running:
            self.running = False
        return True

    async def transmit_audio(self):
        try:
            with self.lock:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1) if self.https else None
                async with websockets.connect(self.url, ssl=ssl_context) as ws:
                    try:
                        config_message = json.dumps(self.config)
                        await ws.send(config_message)
                        response = json.loads(await ws.recv())
                        msg_type = response.get('type', '')
                        if msg_type == 'start':
                            while self.running or ws.closed:
                                data = self.audio.get_chunk(0.25)
                                if not data:
                                    break
                                await ws.send(data)
                        elif msg_type == 'error':
                            print('Server rejected config: {0}'.format(response.get('message', '')))
                        else:
                            print('Server rejected configuration settings...closing connection.')
                    except Exception as e:
                        print('Audio transmission failed: {0}.'.format(e))
        except Exception as e:
            print('Failed to connect to server: {0}'.format(e))
        finally:
            print('Audio transmission stopped.')

class WaveParser():

    def __init__(self, filename):
        self.sample_rate, self.data = wavfile.read(filename)
        self.depth = np.dtype(type(self.data[0][0])).itemsize
        self.channels = self.data.shape[1]
        self.data = self.data.flatten()
        self.cur_index = 0

    def get_chunk(self, chunk):
        chunk_size = int(chunk * self.sample_rate) * self.channels
        start_pos = self.cur_index
        self.cur_index = min(self.cur_index + chunk_size, len(self.data))
        self.sleep_time = ((self.cur_index - start_pos) / self.channels) / self.sample_rate
        time.sleep(self.sleep_time) # Simulates realtime by sleeping between chunks.
        if start_pos == self.cur_index:
            return b''
        return self.data[start_pos:self.cur_index].tobytes()


