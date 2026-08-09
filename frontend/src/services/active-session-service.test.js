import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// The service touches window.location at construction (ApiService); stub it.
beforeEach(() => {
    vi.stubGlobal("window", { location: { protocol: "https:", host: "x.test" } })
})
afterEach(() => vi.unstubAllGlobals())

const { ActiveSessionService } = await import("./active-session-service")

const ok = (body) => ({ status: 200, json: () => Promise.resolve(body) })

function makeService(sessionResp, devicesResp) {
    const svc = new ActiveSessionService()
    svc.initializeSocket = () => {} // don't open a real socket in the happy path
    svc.sessionService = {
        getSession: () => Promise.resolve(sessionResp),
        getSessionDevices: () => Promise.resolve(devicesResp),
    }
    return svc
}

// Regression: initialize() used to advance ONLY on the full 200/200/parse
// happy path and do nothing otherwise, so a 401 (expired login) or any non-200
// left the session page spinner up forever. It must now report an outcome in
// every case so the page can redirect / show an error instead of hanging.
describe("ActiveSessionService.initialize always reports an outcome", () => {
    it("reports ready on the full happy path", async () => {
        const svc = makeService(ok({ id: 414, name: "s", creation_date: "2026-08-09 00:00:00 UTC", end_date: null }), ok([{ id: 1 }]))
        const results = []
        await svc.initialize(414, (r) => results.push(r))
        expect(results).toEqual([{ status: "ready" }])
    })

    it("reports error with httpStatus 401 when the session call is unauthorized", async () => {
        const svc = makeService({ status: 401, json: () => Promise.resolve({}) }, ok([]))
        const results = []
        await svc.initialize(414, (r) => results.push(r))
        expect(results).toEqual([{ status: "error", httpStatus: 401 }])
    })

    it("reports error with httpStatus when the devices call fails (e.g. 404)", async () => {
        const svc = makeService(ok({ id: 414, creation_date: "2026-08-09 00:00:00 UTC", end_date: null }), { status: 404, json: () => Promise.resolve({}) })
        const results = []
        await svc.initialize(414, (r) => results.push(r))
        expect(results).toEqual([{ status: "error", httpStatus: 404 }])
    })

    it("reports error (never hangs) when a call rejects", async () => {
        const svc = makeService(ok({ id: 414, creation_date: "2026-08-09 00:00:00 UTC", end_date: null }), ok([]))
        svc.sessionService.getSession = () => Promise.reject(new Error("network down"))
        const results = []
        await svc.initialize(414, (r) => results.push(r))
        expect(results).toHaveLength(1)
        expect(results[0].status).toBe("error")
    })
})
