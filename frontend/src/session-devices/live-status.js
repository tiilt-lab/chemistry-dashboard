// Pure logic for the Devices tab: which slots a session expects, what state
// each device is in, and the roll-up counts. No React, no fetch, so it is
// unit-tested on its own.

// A transcript that ended within this many seconds counts as "speaking".
export const SPEAKING_WINDOW_S = 30
// Streaming audio but no speech recognised for this long: something is wrong
// with the microphone, the distance to it, or the room is simply quiet.
export const QUIET_WARN_S = 120
// A pod that has only just started streaming gets this long before "no
// speech yet" becomes a warning; speech takes ~15-25 s to be recognised.
export const LISTENING_GRACE_MS = 90000
// The audio service reports each pod's clock (drift from real time, and the
// corrections it has made). Uncorrected drift past this is worth a look: the
// pod's transcript times are off by that much.
export const CLOCK_WARN_S = 3

export function formatAge(seconds) {
    if (seconds == null || isNaN(seconds)) return "—"
    const s = Math.max(0, Math.round(seconds))
    if (s < 60) return `${s} s`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m} min`
    const h = Math.floor(m / 60)
    return `${h} h ${m % 60} min`
}

// The slots a session's pod setup expects, in setup order:
// [{group, team}], team null when one device records the whole group.
export function expectedSlots(podConfig) {
    if (!podConfig || typeof podConfig !== "object") return []
    let groups = Array.isArray(podConfig.groups) ? podConfig.groups : []
    if (!groups.length && podConfig.group_count) {
        const prefix = podConfig.group_prefix || "Group"
        groups = Array.from({ length: Number(podConfig.group_count) }, (_, i) => `${prefix} ${i + 1}`)
    }
    const teams = Array.isArray(podConfig.teams) ? podConfig.teams.map((t) => t && t.name).filter(Boolean) : []
    const perTeam = podConfig.devices_per_group === "team" && teams.length === 2
    const slots = []
    for (const group of groups) {
        if (perTeam) for (const team of teams) slots.push({ group, team })
        else slots.push({ group, team: null })
    }
    return slots
}

// The clock note for a device, or null: a warning while its audio runs
// more than CLOCK_WARN_S from real time, a quiet note once the service has
// corrected it (so a reader knows why earlier times moved).
export function clockNote(d) {
    const c = d && d.clock
    if (!c) return null
    const drift = Number(c.drift) || 0
    const corrected = (Number(c.corrected) || 0) + (Number(c.late_start) || 0) + (Number(c.discarded) || 0)
    if (Math.abs(drift) > CLOCK_WARN_S) {
        const n = Math.round(Math.abs(drift))
        return {
            key: "clock-drift",
            label: `clock ${drift > 0 ? "−" : "+"}${n} s`,
            tone: "orange",
            attention: true,
            hint: `This laptop's audio is running ${n} s ${drift > 0 ? "behind" : "ahead of"} real time, so its transcript times are off by that much until the server corrects it.`,
        }
    }
    if (corrected >= 1) {
        const n = Math.round(corrected)
        return {
            key: "clock-corrected",
            label: `clock corrected ${n} s`,
            tone: "neutral",
            attention: false,
            hint: `The server moved this laptop's clock by ${n} s to match real time.`,
        }
    }
    return null
}

const norm = (v) => (v == null ? "" : String(v).trim().toLowerCase())
const slotKey = (group, team) => `${norm(group)}\u0000${norm(team)}`

// The state of one device from the live payload. opts.sinceStreamingMs is
// how long the dashboard has seen this device streaming (null = never).
export function deviceState(d, opts = {}) {
    if (!d) {
        return { key: "not-joined", label: "Not joined", tone: "neutral", attention: false, hint: "No device has picked this slot yet." }
    }
    if (!d.connected) {
        return { key: "offline", label: "Offline", tone: "danger", attention: true, hint: "The device left or lost its connection." }
    }
    if (d.streaming === false) {
        return { key: "not-recording", label: "Joined, not recording", tone: "orange", attention: true, hint: "Connected, but no audio is being sent. Press Start recording on the device." }
    }
    const age = d.last_speech_age
    if (age != null && age <= SPEAKING_WINDOW_S) {
        return { key: "speaking", label: "Speaking", tone: "teal", pulse: true, attention: false, hint: "Speech was recognised in the last half minute." }
    }
    if (d.streaming == null) {
        // Redis unreachable: connection and speech are all we know.
        return { key: "online", label: "Online", tone: "teal", dot: true, attention: false, hint: "Connected. Whether audio is streaming could not be checked." }
    }
    if (age != null && age <= QUIET_WARN_S) {
        return { key: "quiet", label: "Receiving audio", tone: "teal", dot: true, attention: false, hint: `Audio is streaming; last speech ${formatAge(age)} ago.` }
    }
    const since = opts.sinceStreamingMs
    if (age == null && (since == null || since < LISTENING_GRACE_MS)) {
        return { key: "listening", label: "Listening…", tone: "brand", dot: true, attention: false, hint: "Audio is streaming; the first speech has not been recognised yet." }
    }
    return {
        key: "no-speech",
        label: age == null ? "No speech yet" : `No speech for ${formatAge(age)}`,
        tone: "orange",
        pulse: true,
        attention: true,
        hint: "Audio is streaming but nothing is being recognised. Check the microphone and that people are speaking near it.",
    }
}

// One row per device, in slot order, with an empty row for every slot nobody
// has joined; devices outside the setup (free-form groups, pods of a session
// without a setup) follow under their own name.
// streamingSince: {deviceId: ms when first seen streaming}; now: ms.
export function buildRows(podConfig, devices, { streamingSince = {}, now = Date.now() } = {}) {
    const slots = expectedSlots(podConfig)
    const bySlot = new Map()
    const strays = []
    for (const d of devices || []) {
        if (!d || d.removed) continue
        const key = d.negotiation_group ? slotKey(d.negotiation_group, d.negotiation_side) : null
        const keyNoTeam = d.negotiation_group ? slotKey(d.negotiation_group, null) : null
        const target = key !== null && slots.some((s) => slotKey(s.group, s.team) === key)
            ? key
            : keyNoTeam !== null && slots.some((s) => slotKey(s.group, s.team) === keyNoTeam)
              ? keyNoTeam
              : null
        if (target === null) strays.push(d)
        else {
            if (!bySlot.has(target)) bySlot.set(target, [])
            bySlot.get(target).push(d)
        }
    }
    const row = (slot, device, first) => {
        const since = device && streamingSince[device.id] != null ? now - streamingSince[device.id] : null
        return {
            slotLabel: slot ? [slot.group, slot.team].filter(Boolean).join(" · ") : device ? device.name || "Group" : "",
            inSetup: !!slot,
            first,
            device,
            state: deviceState(device, { sinceStreamingMs: since }),
            clock: clockNote(device),
        }
    }
    const rows = []
    for (const slot of slots) {
        const here = bySlot.get(slotKey(slot.group, slot.team)) || []
        if (!here.length) rows.push(row(slot, null, true))
        else here.forEach((d, i) => rows.push(row(slot, d, i === 0)))
    }
    for (const d of strays) rows.push(row(null, d, true))
    return rows
}

export function summarize(rows) {
    const out = { slots: 0, joined: 0, devices: 0, connected: 0, streaming: 0, speaking: 0, attention: 0 }
    const joinedSlots = new Set()
    for (const r of rows) {
        if (r.first && r.inSetup) out.slots += 1
        if (r.device) {
            out.devices += 1
            if (r.inSetup) joinedSlots.add(r.slotLabel)
            if (r.device.connected) out.connected += 1
            if (r.device.streaming) out.streaming += 1
            if (r.state.key === "speaking") out.speaking += 1
        }
        if (r.state.attention || (r.clock && r.clock.attention)) out.attention += 1
    }
    out.joined = joinedSlots.size
    return out
}
