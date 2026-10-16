import { describe, expect, it } from "vitest"
import { FRAME_HEADER_BYTES, frameSeconds, readStamp, stampedFrame } from "./audio-frame"

describe("stamped audio frames", () => {
    it("prepends the capture time and keeps the samples byte for byte", () => {
        const samples = new Float32Array([0.5, -0.25, 1])
        const buf = stampedFrame({ t: 123.456, samples })
        expect(buf.byteLength).toBe(FRAME_HEADER_BYTES + 12)
        expect(readStamp(buf)).toBeCloseTo(123.456, 9)
        expect(Array.from(new Float32Array(buf, FRAME_HEADER_BYTES))).toEqual([0.5, -0.25, 1])
    })
    it("accepts a bare Float32Array from an older worklet, with no stamp", () => {
        const buf = stampedFrame(new Float32Array([1, 2]))
        expect(Number.isNaN(readStamp(buf))).toBe(true)
        expect(buf.byteLength).toBe(FRAME_HEADER_BYTES + 8)
    })
    it("measures the audio in a frame without the header", () => {
        const buf = stampedFrame({ t: 0, samples: new Float32Array(16000) })
        expect(frameSeconds(buf, 16000)).toBe(1)
    })
})
