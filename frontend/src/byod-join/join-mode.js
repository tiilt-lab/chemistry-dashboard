// What the "Join with" list opens on for a session, from the passcode
// lookup's session JSON (server: join_mode.py). Only an explicit "video"
// opens on Video; a missing or unknown value, or no session yet, is Audio.
// Pure, so it is unit-tested on its own.
export function joinWithDefault(session) {
    return session && session.join_mode === "video" ? "Video" : "Audio"
}
