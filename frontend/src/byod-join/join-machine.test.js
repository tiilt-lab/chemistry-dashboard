import { describe, it, expect } from "vitest"
import { deriveJoinPhase, isLegalTransition } from "./join-machine"

const S = (o = {}) => ({
    audioSocketOpen: false,
    videoSocketOpen: false,
    audioReady: false,
    videoReady: false,
    speakersValidated: false,
    startDiscussionStreaming: false,
    ...o,
})
const C = (o = {}) => ({
    joined: false,
    connectRequested: false,
    armed: false,
    currentForm: "",
    ending: false,
    joinwith: "Audio",
    ...o,
})

describe("deriveJoinPhase", () => {
    it("starts on the form", () => {
        expect(deriveJoinPhase(S(), C())).toBe("form")
    })
    it("pre-join 'Connecting' still shows the form (dialog overlays it)", () => {
        expect(deriveJoinPhase(S(), C({ currentForm: "Connecting" }))).toBe("form")
    })
    it("enrolling right after the REST join, with no sockets at all", () => {
        expect(deriveJoinPhase(S(), C({ joined: true }))).toBe("enrolling")
    })
    it("stays enrolling while sockets are closed until the roster is confirmed", () => {
        expect(
            deriveJoinPhase(S({ audioSocketOpen: false }), C({ joined: true })),
        ).toBe("enrolling")
    })
    it("connecting once the roster is confirmed, until validation", () => {
        const ctx = C({ joined: true, connectRequested: true })
        expect(deriveJoinPhase(S(), ctx)).toBe("connecting")
        expect(
            deriveJoinPhase(S({ audioSocketOpen: true, audioReady: true }), ctx),
        ).toBe("connecting") // still connecting: validation happens via replay
    })
    it("connecting if audio drops after validation (live screen tolerates video drop)", () => {
        const ctx = C({ joined: true, connectRequested: true })
        const validated = S({ audioSocketOpen: true, speakersValidated: true })
        // audio down -> connecting
        expect(deriveJoinPhase(validated, ctx)).toBe("connecting")
        // audio up, video down -> still live (ready), matching the live gate
        expect(
            deriveJoinPhase(
                { ...validated, audioReady: true, videoReady: false },
                { ...ctx, joinwith: "Video" },
            ),
        ).toBe("ready")
    })
    it("ready after validation, recording only once armed + streaming", () => {
        const ctx = C({ joined: true, connectRequested: true })
        const base = S({ audioSocketOpen: true, audioReady: true, speakersValidated: true })
        expect(deriveJoinPhase(base, ctx)).toBe("ready")
        expect(
            deriveJoinPhase(
                { ...base, startDiscussionStreaming: true },
                { ...ctx, armed: true },
            ),
        ).toBe("recording")
    })
    it("ended is reached from teardown or a closed session", () => {
        expect(deriveJoinPhase(S(), C({ ending: true }))).toBe("ended")
        expect(deriveJoinPhase(S(), C({ currentForm: "ClosedSession" }))).toBe("ended")
    })
})

describe("isLegalTransition", () => {
    it("allows the happy path", () => {
        expect(isLegalTransition("form", "enrolling")).toBe(true)
        expect(isLegalTransition("enrolling", "connecting")).toBe(true)
        expect(isLegalTransition("ready", "recording")).toBe(true)
        expect(isLegalTransition("recording", "connecting")).toBe(true) // reconnect
    })
    it("backing out of speaker setup returns to the form", () => {
        expect(isLegalTransition("enrolling", "form")).toBe(true)
    })
    it("rejects illegal jumps and escapes from terminal", () => {
        expect(isLegalTransition("form", "recording")).toBe(false)
        expect(isLegalTransition("ended", "recording")).toBe(false)
    })
})
