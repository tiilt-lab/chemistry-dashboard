import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// globals.js has helpers that read window (theme); stub it for the node env.
beforeEach(() => {
    vi.stubGlobal("window", { matchMedia: () => ({ matches: false }) })
})
afterEach(() => vi.unstubAllGlobals())

const { formatSeconds, formatHMS, filterSortByDevice, buildSpeakerColors, speakerColorFor } = await import("./globals")

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
