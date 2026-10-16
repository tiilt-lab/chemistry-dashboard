import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// The service touches window.location at construction (ApiService); stub it.
beforeEach(() => {
    vi.stubGlobal("window", { location: { protocol: "https:", host: "x.test" } })
    vi.spyOn(console, "warn").mockImplementation(() => {})
    vi.useFakeTimers()
})
afterEach(() => {
    vi.useRealTimers()
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

async function started() {
    const svc = new ActiveSessionService()
    let socket = null
    svc.socketService = { createSocket: () => (socket = fakeSocket()) }
    svc.sessionService = {
        getSession: () => Promise.resolve(ok(SESSION)),
        getSessionDevices: () => Promise.resolve(ok([{ id: 1 }])),
    }
    await svc.initialize(414, () => {})
    return { svc, socket }
}

const row = (id) => ({ transcript: { id, session_device_id: 1, start_time: id, keywords: [] }, speaker_metrics: [] })

// The history arrives in several digest pages within milliseconds. A page
// that subscribed to the store used to re-render once per page; the store
// now notifies once per burst, and says when the history is in.
describe("digest pages are delivered as one burst", () => {
    it("notifies subscribers once after the pages stop, with every row", async () => {
        const { svc, socket } = await started()
        const seen = []
        svc.getTranscripts().subscribe((rows) => seen.push(rows.map((t) => t.id)))
        expect(seen).toEqual([[]]) // the BehaviorSubject's current value

        socket.emit("transcript_metrics_digest", JSON.stringify([row(1), row(2)]))
        socket.emit("transcript_metrics_digest", JSON.stringify([row(3)]))
        // The value is current at once; the notification waits for the burst to end.
        expect(svc.getTranscripts().getValue().map((t) => t.id)).toEqual([1, 2, 3])
        expect(seen).toHaveLength(1)
        expect(svc.transcriptsReady.getValue()).toBe(false)

        vi.advanceTimersByTime(100)
        expect(seen).toEqual([[], [1, 2, 3]])
        expect(svc.transcriptsReady.getValue()).toBe(true)
    })

    it("an empty session is ready after its (empty) digest", async () => {
        const { svc, socket } = await started()
        socket.emit("transcript_metrics_digest", JSON.stringify([]))
        vi.advanceTimersByTime(100)
        expect(svc.transcriptsReady.getValue()).toBe(true)
        expect(svc.getTranscripts().getValue()).toEqual([])
    })

    it("a live row still notifies at once, and close() forgets readiness", async () => {
        const { svc, socket } = await started()
        const seen = []
        svc.getTranscripts().subscribe((rows) => seen.push(rows.map((t) => t.id)))
        socket.emit("transcript_metrics_update", JSON.stringify(row(9)))
        expect(seen).toEqual([[], [9]])

        socket.emit("transcript_metrics_digest", JSON.stringify([row(1)]))
        vi.advanceTimersByTime(100)
        expect(svc.transcriptsReady.getValue()).toBe(true)
        svc.close()
        expect(svc.transcriptsReady.getValue()).toBe(false)
        expect(svc.getTranscripts().getValue()).toEqual([])
    })
})
