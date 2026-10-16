// The wire format of one audio frame to the audio service when the start
// message said frame_timestamps: true: an 8-byte little-endian float64, the
// AudioContext time (seconds) of the frame's first sample, followed by the
// float32 samples. The server maps context time to the session clock once,
// from the start message's context_time, so every frame lands where it was
// captured even when the network held it back or a reconnect replayed it.
export const FRAME_HEADER_BYTES = 8

// The worklet posts {t, samples}; older builds posted a bare Float32Array.
export function stampedFrame(message) {
    const samples = message && message.samples ? message.samples : message
    const t = message && typeof message.t === "number" ? message.t : NaN
    const bytes = samples.byteLength != null ? samples.byteLength : samples.buffer.byteLength
    const out = new ArrayBuffer(FRAME_HEADER_BYTES + bytes)
    new DataView(out).setFloat64(0, t, true)
    new Uint8Array(out, FRAME_HEADER_BYTES).set(
        new Uint8Array(samples.buffer || samples, samples.byteOffset || 0, bytes),
    )
    return out
}

// The seconds of audio in a stamped frame (for the backlog bookkeeping).
export function frameSeconds(buf, sampleRate) {
    return (buf.byteLength - FRAME_HEADER_BYTES) / (4 * sampleRate)
}

export function readStamp(buf) {
    return new DataView(buf).getFloat64(0, true)
}
