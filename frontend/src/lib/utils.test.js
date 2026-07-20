import { describe, it, expect } from "vitest"
import { fmtClock, defaultGroupName } from "./utils"

describe("fmtClock", () => {
    it("formats sub-minute and minute values with zero-padded seconds", () => {
        expect(fmtClock(0)).toBe("0:00")
        expect(fmtClock(5)).toBe("0:05")
        expect(fmtClock(65)).toBe("1:05")
        expect(fmtClock(600)).toBe("10:00")
    })
    it("rounds and clamps negatives to zero", () => {
        expect(fmtClock(50.4)).toBe("0:50")
        expect(fmtClock(50.6)).toBe("0:51")
        expect(fmtClock(-3)).toBe("0:00")
    })
})

describe("defaultGroupName", () => {
    it("is always 'Group NNN' with a 3-digit suffix", () => {
        for (const r of [0, 0.5, 0.999]) {
            expect(defaultGroupName(() => r)).toMatch(/^Group \d{3}$/)
        }
    })
    it("suffix stays in [100, 999]", () => {
        expect(defaultGroupName(() => 0)).toBe("Group 100")
        expect(defaultGroupName(() => 0.9999)).toBe("Group 999")
    })
})
