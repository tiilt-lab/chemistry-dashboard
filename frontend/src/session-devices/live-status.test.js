import { describe, it, expect } from "vitest"
import { expectedSlots, deviceState, buildRows, summarize, formatAge, QUIET_WARN_S, LISTENING_GRACE_MS } from "./live-status"

const viking = {
    groups: ["Group 1", "Group 2"],
    teams: [{ name: "Pat", size: 3 }, { name: "Sandy", size: 3 }],
    devices_per_group: "team",
    group_size: 6,
}

describe("expected slots", () => {
    it("lists one slot per team when each team records from its own device", () => {
        expect(expectedSlots(viking)).toEqual([
            { group: "Group 1", team: "Pat" }, { group: "Group 1", team: "Sandy" },
            { group: "Group 2", team: "Pat" }, { group: "Group 2", team: "Sandy" },
        ])
    })
    it("lists one slot per group otherwise, and builds names from a count + prefix", () => {
        expect(expectedSlots({ group_count: 3, group_prefix: "Table", teams: [], devices_per_group: "group" }))
            .toEqual([{ group: "Table 1", team: null }, { group: "Table 2", team: null }, { group: "Table 3", team: null }])
        expect(expectedSlots(null)).toEqual([])
    })
})

describe("device state", () => {
    const base = { id: 1, connected: true, streaming: true, last_speech_age: 10, utterances: 3 }
    it("not joined / offline / joined-but-not-recording need attention except the first", () => {
        expect(deviceState(null).key).toBe("not-joined")
        expect(deviceState({ ...base, connected: false })).toMatchObject({ key: "offline", attention: true })
        expect(deviceState({ ...base, streaming: false })).toMatchObject({ key: "not-recording", attention: true })
    })
    it("speaking within 30 s, receiving audio within 2 min, then a mic warning", () => {
        expect(deviceState(base).key).toBe("speaking")
        expect(deviceState({ ...base, last_speech_age: 90 })).toMatchObject({ key: "quiet", attention: false })
        expect(deviceState({ ...base, last_speech_age: QUIET_WARN_S + 1 })).toMatchObject({ key: "no-speech", attention: true })
    })
    it("a fresh stream with no speech yet is 'listening' until the grace period passes", () => {
        const fresh = { ...base, last_speech_age: null }
        expect(deviceState(fresh, { sinceStreamingMs: 1000 }).key).toBe("listening")
        expect(deviceState(fresh, { sinceStreamingMs: null }).key).toBe("listening")
        expect(deviceState(fresh, { sinceStreamingMs: LISTENING_GRACE_MS + 1 })).toMatchObject({ key: "no-speech", label: "No speech yet", attention: true })
    })
    it("falls back to a plain Online when streaming could not be checked", () => {
        expect(deviceState({ ...base, streaming: null, last_speech_age: 500 }).key).toBe("online")
        expect(deviceState({ ...base, streaming: null, last_speech_age: 5 }).key).toBe("speaking")
    })
})

describe("rows", () => {
    const devices = [
        { id: 11, name: "Group 1 Pat", negotiation_group: "Group 1", negotiation_side: "Pat", connected: true, streaming: true, last_speech_age: 5, utterances: 40 },
        { id: 12, name: "Group 1 Pat 2", negotiation_group: "Group 1", negotiation_side: "Pat", connected: true, streaming: true, last_speech_age: 400, utterances: 2 },
        { id: 13, name: "Group 2 Sandy", negotiation_group: "Group 2", negotiation_side: "sandy", connected: false, streaming: false, last_speech_age: 900, utterances: 9 },
        { id: 14, name: "Hallway", negotiation_group: null, negotiation_side: null, connected: true, streaming: false, last_speech_age: null, utterances: 0 },
        { id: 15, name: "gone", negotiation_group: "Group 2", negotiation_side: "Pat", removed: true, connected: false },
    ]
    it("keeps setup order, stacks extra devices under their slot, matches teams case-insensitively, appends strays", () => {
        const rows = buildRows(viking, devices, { streamingSince: { 12: 0 }, now: LISTENING_GRACE_MS * 2 })
        expect(rows.map((r) => [r.slotLabel, r.device && r.device.id, r.state.key])).toEqual([
            ["Group 1 · Pat", 11, "speaking"],
            ["Group 1 · Pat", 12, "no-speech"],
            ["Group 1 · Sandy", null, "not-joined"],
            ["Group 2 · Pat", null, "not-joined"],
            ["Group 2 · Sandy", 13, "offline"],
            ["Hallway", 14, "not-recording"],
        ])
        expect(rows.map((r) => r.first)).toEqual([true, false, true, true, true, true])
    })
    it("rolls up joined slots, streaming, speaking and attention counts", () => {
        const rows = buildRows(viking, devices, { streamingSince: {}, now: 0 })
        expect(summarize(rows)).toEqual({ slots: 4, joined: 2, devices: 4, connected: 3, streaming: 2, speaking: 1, attention: 3 })
    })
    it("a session without a setup lists its pods by name", () => {
        const rows = buildRows(null, [devices[3]])
        expect(rows).toHaveLength(1)
        expect(rows[0].slotLabel).toBe("Hallway")
        expect(summarize(rows).slots).toBe(0)
    })
})

describe("ages", () => {
    it("formats seconds, minutes and hours", () => {
        expect(formatAge(7)).toBe("7 s")
        expect(formatAge(125)).toBe("2 min")
        expect(formatAge(3700)).toBe("1 h 1 min")
        expect(formatAge(null)).toBe("—")
    })
})
