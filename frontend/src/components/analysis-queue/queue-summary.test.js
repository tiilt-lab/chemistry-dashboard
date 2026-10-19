import { describe, it, expect } from "vitest"
import { summarizeQueue, legLabel, laneOf, fmtEta, fmtDuration } from "./queue-summary"

const job = (id, session_id, state, legs, extra = {}) => ({
    id, session_id, device_id: 100 + id, state, legs, error: null,
    session_name: `S${session_id}`, device_name: `Pod ${id}`, ...extra,
})

describe("legLabel / laneOf", () => {
    it("names the legs and falls back to the historic audio + video run", () => {
        expect(legLabel(job(1, 1, "queued", ["audio", "rename"]))).toBe("Transcription + Naming")
        expect(legLabel(job(1, 1, "queued", ["coding"]))).toBe("Coding")
        expect(legLabel(job(1, 1, "queued", null))).toBe("Transcription + Video")
        expect(legLabel(job(1, 1, "queued", ["later"]))).toBe("later")
    })
    it("puts only coding-only jobs on the coding lane", () => {
        expect(laneOf(job(1, 1, "queued", ["coding"]))).toBe("coding")
        expect(laneOf(job(1, 1, "queued", ["audio", "coding"]))).toBe("gpu")
        expect(laneOf(job(1, 1, "queued", []))).toBe("gpu")
    })
})

describe("summarizeQueue", () => {
    it("counts states, progress, and groups in queue order", () => {
        const jobs = [
            job(1, 1, "done", ["audio"], { started_at: 0, finished_at: 600 }),
            job(2, 2, "running", ["audio"], { started_at: 600 }),
            job(3, 1, "queued", ["audio"]),
            job(4, 1, "error", ["coding"], { error: "boom" }),
        ]
        const s = summarizeQueue(jobs, { now: 900 })
        expect([s.done.length, s.running.length, s.queued.length, s.errors.length]).toEqual([1, 1, 1, 1])
        expect(s.total).toBe(4)
        expect(s.finished).toBe(2)
        expect(s.pct).toBe(50)
        expect(s.groups.map((g) => [g.id, g.jobs.map((j) => j.id)])).toEqual([[1, [1, 3, 4]], [2, [2]]])
        expect(s.ahead).toBe(0)
    })

    it("scopes to one session and counts other sessions' work ahead of it", () => {
        const jobs = [
            job(1, 9, "running", ["audio"], { started_at: 0 }),
            job(2, 7, "queued", ["audio"]),
            job(3, 9, "queued", ["audio"]),
            job(4, 7, "queued", ["audio"]), // behind this session's last waiting job
            job(5, 9, "done", ["coding"], { started_at: 0, finished_at: 60 }),
        ]
        const s = summarizeQueue(jobs, { sessionId: 9, now: 100 })
        expect(s.total).toBe(3)
        expect(s.ahead).toBe(1)
        expect(s.groups).toHaveLength(1)
        expect(summarizeQueue(jobs, { sessionId: 7, now: 100 }).ahead).toBe(2)
        expect(summarizeQueue(jobs, { sessionId: 5, now: 100 }).total).toBe(0)
    })

    it("has no projection until a job has finished", () => {
        const jobs = [job(1, 1, "running", ["audio"], { started_at: 0 }), job(2, 1, "queued", ["audio"])]
        expect(summarizeQueue(jobs, { now: 50 }).eta).toBeNull()
        expect(summarizeQueue([job(1, 1, "done", ["audio"], { started_at: 0, finished_at: 10 })]).eta).toBeNull()
    })

    it("projects each lane from its own finished jobs and reports the longer one", () => {
        const jobs = [
            job(1, 1, "done", ["audio"], { started_at: 0, finished_at: 600 }), // gpu avg 600
            job(2, 1, "done", ["coding"], { started_at: 0, finished_at: 100 }), // coding avg 100
            job(3, 1, "running", ["audio"], { started_at: 1000 }), // 200 s in: 400 left
            job(4, 1, "queued", ["audio"]), // + 600
            job(5, 1, "running", ["coding"], { started_at: 1150 }), // 50 in: 50 left
            job(6, 1, "queued", ["coding"]), // + 100
        ]
        expect(summarizeQueue(jobs, { now: 1200 }).eta).toBe(1000)
    })

    it("borrows the other lane's average before a lane has finished anything", () => {
        const jobs = [
            job(1, 1, "done", ["audio"], { started_at: 0, finished_at: 600 }),
            job(2, 1, "queued", ["coding"]),
        ]
        expect(summarizeQueue(jobs, { now: 700 }).eta).toBe(600)
    })

    it("never shows a running job as already over", () => {
        const jobs = [
            job(1, 1, "done", ["audio"], { started_at: 0, finished_at: 600 }),
            job(2, 1, "running", ["audio"], { started_at: 600 }),
        ]
        expect(summarizeQueue(jobs, { now: 2000 }).eta).toBe(30)
    })
})

describe("formatting", () => {
    it("rounds the ETA to the unit a person reads", () => {
        expect(fmtEta(20)).toBe("under a minute")
        expect(fmtEta(150)).toBe("~3m")
        expect(fmtEta(3900)).toBe("~1h 5m")
        expect(fmtEta(0)).toBeNull()
    })
    it("formats a finished job's duration", () => {
        expect(fmtDuration(65)).toBe("1m 05s")
        expect(fmtDuration(9)).toBe("9s")
    })
})
