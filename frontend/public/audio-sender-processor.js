// Captures the microphone in the audio thread and posts buffers of 4096
// samples to the page, each stamped with the AudioContext time of its first
// sample. The stamp is what lets the server place the audio on the session
// clock whatever the network did in between: a frame held back for seconds
// and sent in a burst, or replayed after a reconnect, still lands where it
// was captured. `currentTime` here is the context time at the start of the
// current render quantum.
class AudioSenderProcessor extends AudioWorkletProcessor {
  bufferSize = 4096; //16384

  _bytesWritten = 0;

  _buffer = new Float32Array(this.bufferSize);

  // Context time of the first sample in _buffer; null while empty.
  _bufferStart = null;

  process(inputs) {
    this.append(inputs[0][0]);

    return true;
  }

  constructor() {
    super();
    this.initBuffer();
  }

  append(channelData) {
    if (this.isBufferFull()) {
      this.flush();
    }

    if (!channelData) return;

    if (this._bufferStart === null) {
      // Samples already in the buffer came from earlier quanta; this quantum
      // starts `_bytesWritten` samples after the buffer's first sample.
      this._bufferStart = currentTime - this._bytesWritten / sampleRate;
    }
    for (let i = 0; i < channelData.length; i++) {
      this._buffer[this._bytesWritten++] = channelData[i];
    }
  }

  initBuffer() {
    this._bytesWritten = 0;
    this._bufferStart = null;
  }

  isBufferEmpty() {
    return this._bytesWritten === 0;
  }

  isBufferFull() {
    return this._bytesWritten === this.bufferSize;
  }

  flush() {
    const samples =
      this._bytesWritten < this.bufferSize
        ? this._buffer.slice(0, this._bytesWritten)
        : this._buffer.slice();
    this.port.postMessage({ t: this._bufferStart, samples });
    this.initBuffer();
  }
}

registerProcessor("audio-sender-processor", AudioSenderProcessor);
