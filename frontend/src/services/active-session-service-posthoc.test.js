import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

beforeEach(() => {
    vi.stubGlobal("window", { location: { protocol: "https:", host: "x.test" } })
    vi.spyOn(console, "warn").mockImplementation(() => {})
})
afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
})

const { ActiveSessionService } = await import("./active-session-service")

const ok = (body) => ({ status: 200, json: () => Promise.resolve(body) })
const SESSION = { id: 414, name: "s", creation_date: "2026-08-09 00:00:00 UTC", end_date: null }

function fakeSocket() {
    const handlers = {}
    return {
        handlers,
        on(ev, fn) { handlers[ev] = fn },
        emit(ev, fn) { handlers[ev] && handlers[ev](fn) },
        removeAllListeners() { Object.keys(handlers).forEach((k) => delete handlers[k]) },
        disconnect() {},
    }
}

function withSocket(freshRows) {
    const svc = new ActiveSessionService()
    const created = []
    svc.socketService = {
        createSocket: () => {
            const s = fakeSocket()
            created.push(s)
            return s
        },
    }
    const reloads = []
    svc.sessionService = {
        getSession: () => Promise.resolve(ok(SESSION)),
        getSessionDevices: () => Promise.resolve(ok([{ id: 1, posthoc_analyzed_date: null }, { id: 2 }])),
        getSessionDeviceTranscripts: (sessionId, deviceId) => {
            reloads.push([sessionId, deviceId])
            return Promise.resolve(ok(freshRows || []))
        },
    }
    return { svc, created, reloads }
}

const row = (id, device) => ({ transcript: { id, session_device_id: device, start_time: id, keywords: [] }, speaker_metrics: [] })

describe("a post-hoc rewrite reaches an open page", () => {
    it("drops the pod's rows on analysis_reset and leaves the other pods alone", async () => {
        const { svc, created } = withSocket()
        await svc.initialize(414, () => {})
        const s = created[0]
        s.emit("transcript_metrics_digest", JSON.stringify([row(7, 1), row(8, 2), row(9, 1)]))
        s.emit("analysis_reset", JSON.stringify({ session_device_id: 1, scope: "audio" }))
        expect(svc.transcriptSource.getValue().map((t) => t.id)).toEqual([8])
    })

    it("reloads the pod's rows from the server when its analysed date changes", async () => {
        const fresh = [{ id: 20, session_device_id: 1, start_time: 5, transcript: "new" }, { id: 21, session_device_id: 1, start_time: 9, transcript: "rows" }]
        const { svc, created, reloads } = withSocket(fresh)
        await svc.initialize(414, () => {})
        const s = created[0]
        s.emit("transcript_metrics_digest", JSON.stringify([row(7, 1), row(8, 2)]))
        s.emit("transcript_update", JSON.stringify({ id: 20, session_device_id: 1, start_time: 5, keywords: [] }))
        s.emit("device_update", JSON.stringify({ id: 1, posthoc_analyzed_date: "2026-10-18 21:40:00 UTC" }))
        await new Promise((r) => setTimeout(r, 0))
        await new Promise((r) => setTimeout(r, 0))
        expect(reloads).toEqual([[414, 1]])
        expect(svc.transcriptSource.getValue().map((t) => t.id).sort()).toEqual([20, 21, 8])
        // the same date again is not a new run
        s.emit("device_update", JSON.stringify({ id: 1, posthoc_analyzed_date: "2026-10-18 21:40:00 UTC" }))
        await new Promise((r) => setTimeout(r, 0))
        expect(reloads).toHaveLength(1)
    })
})
