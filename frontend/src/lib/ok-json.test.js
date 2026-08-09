import { describe, it, expect } from "vitest"
import { okJson } from "./utils"

// The "response.status === 200 ? response.json() : fallback" unwrap was
// hand-written ~90 times. okJson is that, once.
describe("okJson", () => {
    it("parses the body on a 200", async () => {
        const res = { status: 200, json: () => Promise.resolve([{ id: 1 }]) }
        expect(await okJson(res, [])).toEqual([{ id: 1 }])
    })
    it("returns the fallback on a non-200 without touching the body", async () => {
        let parsed = false
        const res = { status: 500, json: () => { parsed = true; return Promise.resolve({}) } }
        expect(await okJson(res, [])).toEqual([])
        expect(parsed).toBe(false)
    })
    it("returns the fallback for a null/absent response", async () => {
        expect(await okJson(null, "x")).toBe("x")
        expect(await okJson(undefined)).toBe(null)
    })
})
