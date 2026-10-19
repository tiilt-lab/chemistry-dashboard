import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { ApiService, queryString } from "./api-service"

// The admin log routes and /api/v1/devices read their filters from
// request.args. Until 2026-10-19 the service passed them as "data", which
// _request only ever sent as a body, and never on GET/DELETE: the server
// saw no log_type and "clear the audio log" truncated the server log.

describe("queryString", () => {
    it("serialises scalars and skips null/undefined", () => {
        expect(queryString({ log_type: "aps", n: 3, skip: null, gone: undefined })).toBe("log_type=aps&n=3")
    })
    it("is empty for nothing, non-objects and FormData", () => {
        expect(queryString(undefined)).toBe("")
        expect(queryString({})).toBe("")
        expect(queryString("x")).toBe("")
        expect(queryString(new FormData())).toBe("")
    })
    it("encodes reserved characters", () => {
        expect(queryString({ q: "a b&c" })).toBe("q=a+b%26c")
    })
})

describe("ApiService._request", () => {
    const calls = []
    beforeEach(() => {
        calls.length = 0
        vi.stubGlobal("window", { location: { protocol: "https:", host: "blinc.test" } })
        vi.stubGlobal(
            "fetch",
            vi.fn((url, options) => {
                calls.push({ url, options })
                return Promise.resolve({ status: 200 })
            }),
        )
    })
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it("puts GET parameters on the URL and sends no body", async () => {
        await new ApiService().httpRequestCall("api/v1/admin/server/logs", "GET", { log_type: "aps" })
        expect(calls[0].url).toBe("https://blinc.test/api/v1/admin/server/logs?log_type=aps")
        expect(calls[0].options.body).toBeUndefined()
    })

    it("puts DELETE parameters on the URL and sends no body", async () => {
        await new ApiService().httpRequestCall("api/v1/admin/server/logs", "DELETE", { log_type: "aps" })
        expect(calls[0].url).toBe("https://blinc.test/api/v1/admin/server/logs?log_type=aps")
        expect(calls[0].options.body).toBeUndefined()
    })

    it("appends with & when the path already has a query", async () => {
        await new ApiService().httpRequestCall("api/v1/devices?x=1", "GET", { archived: false, isPod: true })
        expect(calls[0].url).toBe("https://blinc.test/api/v1/devices?x=1&archived=false&isPod=true")
    })

    it("leaves a GET without parameters alone", async () => {
        await new ApiService().httpRequestCall("api/v1/me", "GET", {})
        expect(calls[0].url).toBe("https://blinc.test/api/v1/me")
        await new ApiService().get("api/v1/me")
        expect(calls[1].url).toBe("https://blinc.test/api/v1/me")
    })

    it("still JSON-encodes a POST body and adds no query", async () => {
        await new ApiService().httpRequestCall("api/v1/sessions", "POST", { name: "S" })
        expect(calls[0].url).toBe("https://blinc.test/api/v1/sessions")
        expect(calls[0].options.body).toBe('{"name":"S"}')
    })
})
