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
//
// FLOW (since the deferred-connection rework): the form's Connect-to-server
// does a REST join only — no media, no sockets. Speaker setup happens
// entirely offline (fingerprints queue client-side); confirming the roster
// is what opens the devices and sockets, replays the queued fingerprints
// and validates. Recording therefore cannot have started before the user
// is past the speaker page.

export type JoinPhase =
    | "form" // entering group name / passcode
    | "enrolling" // joined (REST); configuring speakers, no connection yet
    | "connecting" // media + sockets opening (after roster confirm, or reconnect)
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
    joined: boolean // REST join done (a session/device exists)
    connectRequested: boolean // roster confirmed; media + sockets starting
    armed: boolean // Start recording pressed
    currentForm: string // dialog/step string state
    ending: boolean // teardown in progress
    joinwith: string // "Audio" | "Video" | "Videocartoonify"
}

// The single source of truth for "what phase are we in". Each phase maps
// EXACTLY to one render gate in html-pages.jsx, so the gates can read the
// phase instead of re-deriving from flags:
//
//   form       <- not joined (the "Connecting" dialog, if any, overlays it)
//   enrolling  <- joined && !validated && !connectRequested (speaker page,
//                 fully offline — nothing is capturing or connected)
//   connecting <- joined && !validated && connectRequested (devices/sockets
//                 opening; also reconnects, which reset validation)
//   ready      <- validated, live screen up, not recording
//   recording  <- validated + armed + streaming
//   ended      <- teardown / session closed
//
// Once validated the live screen tolerates a video drop, so ready/recording
// gate on audioReady only.
export function deriveJoinPhase(
    s: JoinFlags,
    ctx: JoinContext,
): JoinPhase {
    if (ctx.ending || ctx.currentForm === "ClosedSession") return "ended"
    if (!ctx.joined) return "form"
    if (!s.speakersValidated) {
        return ctx.connectRequested ? "connecting" : "enrolling"
    }
    if (!s.audioReady) return "connecting"
    return s.startDiscussionStreaming && ctx.armed ? "recording" : "ready"
}

// Legal forward transitions — the reference the incremental migration checks
// itself against. Reconnects re-enter `connecting` from `recording`/`ready`;
// backing out of speaker setup returns to `form`. Dismissing the
// session-ended dialog returns to `form` (identity kept) so the pod can
// rejoin the next session — `ended` used to be terminal, which left a
// header-only blank page with no way forward.
export const JOIN_TRANSITIONS: Record<JoinPhase, JoinPhase[]> = {
    form: ["enrolling", "ended"],
    enrolling: ["connecting", "form", "ended"],
    connecting: ["ready", "enrolling", "ended"],
    ready: ["recording", "connecting", "ended"],
    recording: ["connecting", "ended"],
    ended: ["form"],
}

export function isLegalTransition(from: JoinPhase, to: JoinPhase): boolean {
    return from === to || JOIN_TRANSITIONS[from].includes(to)
}
