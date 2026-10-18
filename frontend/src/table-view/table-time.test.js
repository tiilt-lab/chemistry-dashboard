import { describe, it, expect } from "vitest"
import { toDeviceClock, toMergedClock, seekFor, decorateLines, lineAt } from "./table-time"

const alignment = { reference_device: 1, other_device: 2, offsets: [{ at: 100, offset: 2 }, { at: 700, offset: 3 }] }

describe("table clocks", () => {
    it("is the identity on the reference laptop", () => {
        expect(toDeviceClock(150, 1, alignment)).toBe(150)
        expect(toMergedClock(150, 1, alignment)).toBe(150)
        expect(toDeviceClock(150, 2, null)).toBe(150)
    })
    it("applies the nearest offset sample on the other laptop", () => {
        expect(toDeviceClock(150, 2, alignment)).toBe(152)
        expect(toDeviceClock(650, 2, alignment)).toBe(653)
        expect(toMergedClock(152, 2, alignment)).toBe(150)
    })
    it("seeks a laptop's own line by its own stamp", () => {
        const own = { session_device_id: 2, start_time: 148, device_start_time: 150 }
        const other = { session_device_id: 1, start_time: 148 }
        expect(seekFor(own, 2, alignment)).toBe(150)
        expect(seekFor(own, 1, alignment)).toBe(148)
        expect(seekFor(other, 2, alignment)).toBe(150)
        expect(seekFor(null, 2, alignment)).toBe(null)
    })
    it("labels lines by side and finds the playing line", () => {
        const pods = [{ id: 1, side: "Pat", name: "Pat laptop" }, { id: 2, side: null, name: "Sandy laptop" }]
        const lines = decorateLines([{ session_device_id: 1, start_time: 10 }, { session_device_id: 2, start_time: 20 }], pods)
        expect(lines.map((l) => l.pod_label)).toEqual(["Pat", "Sandy laptop"])
        expect(lineAt(lines, 15).start_time).toBe(10)
        expect(lineAt(lines, 25).start_time).toBe(20)
        expect(lineAt(lines, 5)).toBe(null)
    })
})
