import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { ApiService } from "./api-service"

// Guards the merge-count regression: API responses reflect mutable server
// state, so a GET re-fetched right after a mutation must hit the network,
// not a stale browser cache. If someone drops cache:"no-store", this fails.
describe("ApiService caching", () => {
    let calls
    beforeEach(() => {
        calls = []
        // ApiService.getEndpoint reads window.location; stub it (node env).
        vi.stubGlobal("window", {
            location: { protocol: "https:", host: "example.test" },
        })
        global.fetch = vi.fn((url, options) => {
            calls.push({ url, options })
            return Promise.resolve({ status: 200, json: () => Promise.resolve([]) })
        })
    })
    afterEach(() => {
        vi.unstubAllGlobals()
        vi.restoreAllMocks()
    })

    it("GET requests are never browser-cached", () => {
        new ApiService().httpRequestCall("api/v1/students/overview", "GET", {})
        expect(calls).toHaveLength(1)
        expect(calls[0].options.cache).toBe("no-store")
    })

    it("mutations are also uncached", () => {
        new ApiService().httpRequestCall("api/v1/admin/students/1/merge", "POST", {
            targetId: 2,
        })
        expect(calls[0].options.cache).toBe("no-store")
        expect(calls[0].options.method).toBe("POST")
    })
})
