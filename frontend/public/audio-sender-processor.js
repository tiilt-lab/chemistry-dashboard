class AudioSenderProcessor extends AudioWorkletProcessor {

  bufferSize = 4096//16384

  _bytesWritten = 0

  _buffer = new Float32Array(this.bufferSize)

	process(inputs) {
		this.append(inputs[0][0])
    
    return true;
	}
  
  constructor() {
    super();
    this.initBuffer()
  }
  
  append(channelData){
    if(this.isBufferFull()){
      this.flush()
    }

    if(!channelData) return
    
    for(let i = 0; i < channelData.length; i++){
      this._buffer[this._bytesWritten++] = channelData[i]
    }
  }

  initBuffer(){
    this._bytesWritten=0
  }

  isBufferEmpty(){
    return this._bytesWritten === 0
  }

  isBufferFull(){
    return this._bytesWritten === this.bufferSize
  }

  flush(){
    this.port.postMessage(
      this._bytesWritten < this.bufferSize 
      ? this._buffer.slice(0, this._bytesWritten)
      : this._buffer
    )
    this.initBuffer()
  }

}

registerProcessor('audio-sender-processor', AudioSenderProcessor)
