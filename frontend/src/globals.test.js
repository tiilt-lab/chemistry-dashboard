import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// globals.js has helpers that read window (theme); stub it for the node env.
beforeEach(() => {
    vi.stubGlobal("window", { matchMedia: () => ({ matches: false }) })
})
afterEach(() => vi.unstubAllGlobals())

const { formatSeconds, formatHMS, filterSortByDevice, buildSpeakerColors, speakerColorFor, indexSpeakerInfo, speakerLabel, wallClockLabel, TEAM_PALETTES } = await import("./globals")

describe("buildSpeakerColors", () => {
    it("maps each unique speaker tag to its palette color, ignoring blanks", () => {
        const rows = [
            { speaker_tag: "Ada" }, { speaker_tag: "Ada" },
            { speaker_tag: "Bo" }, { speaker_tag: null }, { speaker_tag: "" },
        ]
        const map = buildSpeakerColors(rows)
        expect(Object.keys(map).sort()).toEqual(["Ada", "Bo"])
        expect(map.Ada).toBe(speakerColorFor("Ada", ["Ada", "Bo"]))
        expect(map.Bo).toBe(speakerColorFor("Bo", ["Ada", "Bo"]))
    })
    it("handles empty/absent input", () => {
        expect(buildSpeakerColors([])).toEqual({})
        expect(buildSpeakerColors(undefined)).toEqual({})
    })
})

describe("filterSortByDevice", () => {
    const rows = [
        { session_device_id: 3, start_time: 30 },
        { session_device_id: 7, start_time: 5 },
        { session_device_id: 3, start_time: 10 },
    ]
    it("keeps only the given device and sorts ascending by the key", () => {
        expect(filterSortByDevice(rows, 3, "start_time")).toEqual([
            { session_device_id: 3, start_time: 10 },
            { session_device_id: 3, start_time: 30 },
        ])
    })
    it("coerces a string device id (URL params are strings)", () => {
        expect(filterSortByDevice(rows, "7", "start_time")).toEqual([
            { session_device_id: 7, start_time: 5 },
        ])
    })
    it("returns empty when no row matches, without mutating the input", () => {
        expect(filterSortByDevice(rows, 99, "start_time")).toEqual([])
        expect(rows[0].session_device_id).toBe(3)
    })
})

describe("formatSeconds", () => {
    it("defaults to zero-padded H:MM:SS, dropping a zero hour", () => {
        expect(formatSeconds(0)).toBe("00:00")
        expect(formatSeconds(65)).toBe("01:05")
        expect(formatSeconds(3600)).toBe("01:00:00")
        expect(formatSeconds(3665)).toBe("01:01:05")
    })
    it("truncates fractional seconds", () => {
        expect(formatSeconds(65.9)).toBe("01:05")
    })
    it("padLeading:false leaves the largest unit unpadded (formatDuration style)", () => {
        expect(formatSeconds(65, { padLeading: false })).toBe("1:05")
        expect(formatSeconds(3665, { padLeading: false })).toBe("1:01:05")
    })
    it("alwaysHours shows a zero hour (lengthFormatted style), including past 24h", () => {
        expect(formatSeconds(65, { alwaysHours: true })).toBe("00:01:05")
        expect(formatSeconds(90000, { alwaysHours: true })).toBe("25:00:00")
    })
    it("invalid maps null/NaN to the supplied placeholder", () => {
        expect(formatSeconds(null, { invalid: "—" })).toBe("—")
        expect(formatSeconds(NaN, { invalid: "—" })).toBe("—")
        // without the option, no special-casing (back-compat)
        expect(formatSeconds(5)).toBe("00:05")
    })
})

describe("formatHMS", () => {
    it("is always HH:MM:SS", () => {
        expect(formatHMS(5)).toBe("00:00:05")
        expect(formatHMS(3665)).toBe("01:01:05")
    })
})

describe("team speaker labels and colours", () => {
    const speakers = [
        { alias: "Pat1G1S32", label: "Pat 1", team: "Pat", team_index: 0, index: 1 },
        { alias: "Pat3G1S32", label: "Pat 3", team: "Pat", team_index: 0, index: 3 },
        { alias: "Bo Example", label: "Sandy 2", team: "Sandy", team_index: 1, index: 2 },
        { alias: "Guest", label: "Guest", team: null, team_index: null, index: null },
    ]
    const info = indexSpeakerInfo(speakers)
    it("labels a known speaker by team and leaves the rest as stored", () => {
        expect(speakerLabel("Bo Example", info)).toBe("Sandy 2")
        expect(speakerLabel("Guest", info)).toBe("Guest")
        expect(speakerLabel("Nobody", info)).toBe("Nobody")
        expect(speakerLabel(null, info)).toBe(null)
    })
    it("colours teammates from one palette, shade by place on the team", () => {
        expect(speakerColorFor("Pat1G1S32", [], info)).toBe(TEAM_PALETTES[0][0])
        expect(speakerColorFor("Pat3G1S32", [], info)).toBe(TEAM_PALETTES[0][1])
        expect(speakerColorFor("Bo Example", [], info)).toBe(TEAM_PALETTES[1][0])
        expect(TEAM_PALETTES[0]).not.toContain(speakerColorFor("Bo Example", [], info))
    })
    it("falls back to the shared palette for a speaker without a team", () => {
        expect(speakerColorFor("Guest", ["Guest", "Zed"], info)).toBe(speakerColorFor("Guest", ["Guest", "Zed"]))
        const colors = buildSpeakerColors([{ speaker_tag: "Pat1G1S32" }, { speaker_tag: "Guest" }], info)
        expect(colors["Pat1G1S32"]).toBe(TEAM_PALETTES[0][0])
    })
})

describe("wallClockLabel", () => {
    it("places a session-clock second on the day's clock", () => {
        const base = new Date("2026-10-15T20:31:26Z")
        expect(wallClockLabel(base, 81627, "UTC")).toBe("7:11:53 PM")
        expect(wallClockLabel(base, 81627, "America/Chicago")).toBe("2:11:53 PM")
    })
    it("is blank without a usable base", () => {
        expect(wallClockLabel(null, 10)).toBe("")
        expect(wallClockLabel(new Date("nope"), 10)).toBe("")
        expect(wallClockLabel(new Date(), null)).toBe("")
    })
})
