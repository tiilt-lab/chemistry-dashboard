import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { CodingSchemeService } from "./coding-scheme-service"

describe("CodingSchemeService", () => {
    let calls
    let reply
    beforeEach(() => {
        calls = []
        reply = { status: 200, json: () => Promise.resolve([{ ref: "builtin:negotiation" }]) }
        vi.stubGlobal("window", { location: { protocol: "https:", host: "example.test" } })
        global.fetch = vi.fn((url, options) => {
            calls.push({ url, options })
            return Promise.resolve(reply)
        })
    })
    afterEach(() => {
        vi.unstubAllGlobals()
        vi.restoreAllMocks()
    })

    it("lists, gets by ref, creates, updates, deletes and validates", async () => {
        const svc = new CodingSchemeService()
        expect(await svc.list()).toEqual({ status: 200, body: [{ ref: "builtin:negotiation" }] })
        expect(calls[0].url).toBe("https://example.test/api/v1/coding_schemes")
        await svc.get("scheme:7")
        expect(calls[1].url).toBe("https://example.test/api/v1/coding_schemes/scheme%3A7")
        await svc.create({ name: "x", dimensions: [] })
        expect(calls[2].options.method).toBe("POST")
        expect(JSON.parse(calls[2].options.body)).toEqual({ name: "x", dimensions: [] })
        await svc.update(7, { name: "y", dimensions: [] })
        expect(calls[3].url).toBe("https://example.test/api/v1/coding_schemes/7")
        expect(calls[3].options.method).toBe("PUT")
        await svc.delete(7)
        expect(calls[4].options.method).toBe("DELETE")
        await svc.validate({ name: "" })
        expect(calls[5].url).toBe("https://example.test/api/v1/coding_schemes/validate")
    })

    it("resolves a body-less reply with null", async () => {
        reply = { status: 404, json: () => Promise.reject(new Error("no body")) }
        expect(await new CodingSchemeService().get("scheme:1")).toEqual({ status: 404, body: null })
    })
})
