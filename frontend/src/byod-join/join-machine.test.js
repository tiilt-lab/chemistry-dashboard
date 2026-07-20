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
    deviceCheck: false,
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
    it("shows device check when one is pending pre-connect", () => {
        expect(deriveJoinPhase(S(), C({ deviceCheck: true }))).toBe("device_check")
    })
    it("pre-socket 'Connecting' still shows the form (dialog overlays it)", () => {
        expect(deriveJoinPhase(S(), C({ currentForm: "Connecting" }))).toBe("form")
    })
    it("connecting once the socket is open but not yet ready to enroll", () => {
        expect(deriveJoinPhase(S({ audioSocketOpen: true }), C())).toBe("connecting")
    })
    it("connecting if audio drops after validation (live screen tolerates video drop)", () => {
        const validated = S({ audioSocketOpen: true, speakersValidated: true })
        // audio down -> connecting
        expect(deriveJoinPhase(validated, C())).toBe("connecting")
        // audio up, video down -> still live (ready), matching the live gate
        expect(
            deriveJoinPhase(
                { ...validated, audioReady: true, videoReady: false },
                C({ joinwith: "Video" }),
            ),
        ).toBe("ready")
    })
    it("enrolling once ready but speakers not validated", () => {
        expect(
            deriveJoinPhase(S({ audioSocketOpen: true, audioReady: true }), C()),
        ).toBe("enrolling")
    })
    it("video join needs both sockets ready before enrolling", () => {
        const ctx = C({ joinwith: "Video" })
        expect(
            deriveJoinPhase(S({ audioSocketOpen: true, audioReady: true }), ctx),
        ).toBe("connecting") // video not ready yet
        expect(
            deriveJoinPhase(
                S({
                    audioSocketOpen: true,
                    audioReady: true,
                    videoSocketOpen: true,
                    videoReady: true,
                }),
                ctx,
            ),
        ).toBe("enrolling")
    })
    it("ready after validation, recording only once armed + streaming", () => {
        const base = S({ audioSocketOpen: true, audioReady: true, speakersValidated: true })
        expect(deriveJoinPhase(base, C())).toBe("ready")
        expect(
            deriveJoinPhase({ ...base, startDiscussionStreaming: true }, C({ armed: true })),
        ).toBe("recording")
    })
    it("ended is reached from teardown or a closed session", () => {
        expect(deriveJoinPhase(S(), C({ ending: true }))).toBe("ended")
        expect(deriveJoinPhase(S(), C({ currentForm: "ClosedSession" }))).toBe("ended")
    })
})

describe("isLegalTransition", () => {
    it("allows the happy path", () => {
        expect(isLegalTransition("form", "device_check")).toBe(true)
        expect(isLegalTransition("ready", "recording")).toBe(true)
        expect(isLegalTransition("recording", "connecting")).toBe(true) // reconnect
    })
    it("rejects illegal jumps and escapes from terminal", () => {
        expect(isLegalTransition("form", "recording")).toBe(false)
        expect(isLegalTransition("ended", "recording")).toBe(false)
    })
})
