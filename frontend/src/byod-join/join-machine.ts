// Explicit state machine for the BYOD join flow.
//
// The join component drives recording through a soup of boolean flags
// (audioSocketOpen, videoReady, speakersValidated, armed, currentForm, an
// `ending` ref …) spread across a reducer, useState, and refs. Reading that
// soup from inside chained effects — where the closure captured a stale
// snapshot — caused three production incidents (dead reconnect,
// binary-before-start, ghost dialogs).
//
// STRANGLER-FIG STEP 1: capture the phases and their legal transitions as a
// single pure, tested source of truth WITHOUT changing behavior. The
// component computes `deriveJoinPhase` from its existing flags and exposes it
// (data-join-phase) so rendering/effects can migrate onto it one at a time.
// Later steps move the transition logic itself into `next()`.

export type JoinPhase =
    | "form" // entering group name / passcode
    | "device_check" // camera/mic/channel verification
    | "connecting" // sockets opening (initial or reconnect)
    | "enrolling" // sockets ready, recording speaker fingerprints
    | "ready" // validated, camera live, NOT yet recording
    | "recording" // streaming to the server
    | "ended" // pod recording finished / session closed

export interface JoinFlags {
    audioSocketOpen: boolean
    videoSocketOpen: boolean
    audioReady: boolean
    videoReady: boolean
    speakersValidated: boolean
    startDiscussionStreaming: boolean
}

export interface JoinContext {
    deviceCheck: boolean // a device-check is pending
    armed: boolean // Start recording pressed
    currentForm: string // dialog/step string state
    ending: boolean // teardown in progress
    joinwith: string // "Audio" | "Video" | "Videocartoonify"
}

function wantsVideo(joinwith: string): boolean {
    return joinwith === "Video" || joinwith === "Videocartoonify"
}

// The single source of truth for "what phase are we in", derived from the
// existing flags exactly as the render gates in html-pages.jsx do today.
export function deriveJoinPhase(
    s: JoinFlags,
    ctx: JoinContext,
): JoinPhase {
    if (ctx.ending || ctx.currentForm === "ClosedSession") return "ended"
    if (!s.audioSocketOpen) {
        if (ctx.deviceCheck) return "device_check"
        return ctx.currentForm === "Connecting" ? "connecting" : "form"
    }
    const ready =
        s.audioReady && (!wantsVideo(ctx.joinwith) || (s.videoSocketOpen && s.videoReady))
    if (!ready) return "connecting"
    if (!s.speakersValidated) return "enrolling"
    if (s.startDiscussionStreaming && ctx.armed) return "recording"
    return "ready"
}

// Legal forward transitions — the reference the incremental migration checks
// itself against. Reconnects re-enter `connecting` from `recording`/`ready`;
// `ended` is terminal for a pod.
export const JOIN_TRANSITIONS: Record<JoinPhase, JoinPhase[]> = {
    form: ["device_check", "ended"],
    device_check: ["connecting", "form", "ended"],
    connecting: ["enrolling", "ended"],
    enrolling: ["ready", "connecting", "ended"],
    ready: ["recording", "connecting", "ended"],
    recording: ["connecting", "ended"],
    ended: [],
}

export function isLegalTransition(from: JoinPhase, to: JoinPhase): boolean {
    return from === to || JOIN_TRANSITIONS[from].includes(to)
}
