import { describe, it, expect, vi } from "vitest"

// The panel module imports ApiService, which touches window at import time
// in the node test env.
vi.stubGlobal("window", {
    location: { protocol: "https:", host: "example.test" },
})

const { trendOf, fmtMins, openRatios, giveTake } = await import(
    "./student-longitudinal-panel"
)

describe("trendOf", () => {
    it("needs three sessions before calling a direction", () => {
        expect(trendOf([])).toBe(null)
        expect(trendOf([0.2, 0.3])).toBe(null)
    })
    it("flags monotonic runs over the last three only", () => {
        expect(trendOf([0.1, 0.2, 0.3])).toBe("up")
        expect(trendOf([0.5, 0.4, 0.2])).toBe("down")
        expect(trendOf([0.9, 0.1, 0.2, 0.3])).toBe("up") // early noise ignored
    })
    it("noise is steady, not a false alarm", () => {
        expect(trendOf([0.2, 0.5, 0.3])).toBe("flat")
        expect(trendOf([0.3, 0.3, 0.3])).toBe("flat")
    })
})

describe("fmtMins", () => {
    it("formats m:ss", () => {
        expect(fmtMins(0)).toBe("0:00")
        expect(fmtMins(65)).toBe("1:05")
        expect(fmtMins(680)).toBe("11:20")
    })
    it("tolerates null/negative", () => {
        expect(fmtMins(null)).toBe("0:00")
        expect(fmtMins(-5)).toBe("0:00")
    })
})

describe("giveTake", () => {
    it("keeps only analyzed sessions and normalizes to the shared max", () => {
        const { rows, norm } = giveTake([
            { influence: 0.4, external_relevance: 0.2 },
            { influence: null, external_relevance: null }, // never analyzed
            { influence: 0.1, external_relevance: 0.8 },
        ])
        expect(rows.length).toBe(2)
        expect(norm(0.8)).toBe(100) // shared max across BOTH series
        expect(norm(0.4)).toBe(50)
        expect(norm(null)).toBe(0)
    })
    it("all-null input yields no rows and a zero norm", () => {
        const { rows, norm } = giveTake([{ influence: null, external_relevance: null }])
        expect(rows.length).toBe(0)
        expect(norm(0.5)).toBe(0)
    })
})

describe("openRatios", () => {
    it("skips sessions with no questions and rounds percentages", () => {
        expect(
            openRatios([
                { questions: 13, open_questions: 1 },
                { questions: 0, open_questions: 0 },
                { questions: 32, open_questions: 1 },
            ]),
        ).toEqual([8, 3])
    })
})
