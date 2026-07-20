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

// The single source of truth for "what phase are we in". Each phase maps
// EXACTLY to one render gate in html-pages.jsx, so the gates can read the
// phase instead of re-deriving from flags:
//
//   form         <- !audioSocketOpen && !deviceCheck  (the join form; the
//                   "Connecting" dialog, if any, overlays it separately)
//   device_check <- !audioSocketOpen && deviceCheck
//   connecting   <- audioSocketOpen && not-yet-ready-to-enroll (overlay only,
//                   no main content — a transient waiting state)
//   enrolling    <- audioSocketOpen && ready && !speakersValidated
//   ready        <- validated, live screen up, not recording
//   recording    <- validated + armed + streaming
//   ended        <- teardown / session closed
//
// Note the asymmetry that matches the gates: enrolling needs FULL readiness
// (video too), but once validated the live screen tolerates a video drop, so
// ready/recording gate on audioReady only.
export function deriveJoinPhase(
    s: JoinFlags,
    ctx: JoinContext,
): JoinPhase {
    if (ctx.ending || ctx.currentForm === "ClosedSession") return "ended"
    if (!s.audioSocketOpen) {
        return ctx.deviceCheck ? "device_check" : "form"
    }
    if (!s.speakersValidated) {
        const readyToEnroll =
            s.audioReady &&
            (!wantsVideo(ctx.joinwith) || (s.videoSocketOpen && s.videoReady))
        return readyToEnroll ? "enrolling" : "connecting"
    }
    // Validated: the live screen shows as long as audio is up (matches the
    // live render gate, which does not re-check video).
    if (!s.audioReady) return "connecting"
    return s.startDiscussionStreaming && ctx.armed ? "recording" : "ready"
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
