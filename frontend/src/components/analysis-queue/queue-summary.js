// Pure helpers behind the analysis-queue panel: what each post-hoc job is,
// how far the queue is, and a projected finish. Mirrors src/server/
// posthoc_queue.py: a job carries legs (audio, rename, video, coding); the
// GPU lane runs everything but coding-only jobs one at a time, and the
// coding lane runs coding-only jobs beside it.

export const LEG_LABEL = {
    audio: "Transcription",
    rename: "Naming",
    video: "Video",
    coding: "Coding",
}
const DEFAULT_LEGS = ["audio", "video"] // a job without legs: the historic run
const MIN_REMAINING = 30 // s: a running job never shows as already over

export function jobLegs(job) {
    return job.legs && job.legs.length ? job.legs : DEFAULT_LEGS
}

export function legLabel(job) {
    return jobLegs(job)
        .map((l) => LEG_LABEL[l] || l)
        .join(" + ")
}

export function laneOf(job) {
    const legs = jobLegs(job)
    return legs.length === 1 && legs[0] === "coding" ? "coding" : "gpu"
}

export function fmtEta(seconds) {
    if (seconds == null || !isFinite(seconds) || seconds <= 0) return null
    const h = Math.floor(seconds / 3600)
    const m = Math.round((seconds % 3600) / 60)
    if (h > 0) return `~${h}h ${m}m`
    if (m >= 1) return `~${m}m`
    return "under a minute"
}

// m:ss for a running job, "12m 05s" for a finished one.
export function fmtElapsed(seconds) {
    if (seconds == null || !isFinite(seconds) || seconds < 0) return null
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${String(s).padStart(2, "0")}`
}

export function fmtDuration(seconds) {
    if (seconds == null || !isFinite(seconds) || seconds < 0) return null
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`
}

const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)

// Remaining seconds on one lane: what is left of its running job plus one
// average per queued job. Projected from that lane's finished jobs, or from
// any finished job before the lane has one of its own; null until a job has
// finished at all.
function laneRemaining(jobs, lane, now, fallbackAvg) {
    const mine = jobs.filter((j) => laneOf(j) === lane)
    const durations = mine
        .filter((j) => j.state === "done" && j.started_at != null && j.finished_at != null)
        .map((j) => j.finished_at - j.started_at)
    const avg = mean(durations) ?? fallbackAvg
    const running = mine.filter((j) => j.state === "running")
    const queued = mine.filter((j) => j.state === "queued")
    if (running.length + queued.length === 0) return 0
    if (avg == null) return null
    let left = queued.length * avg
    for (const j of running) {
        const elapsed = j.started_at != null ? now - j.started_at : 0
        left += Math.max(avg - elapsed, MIN_REMAINING)
    }
    return left
}

// jobs: the global queue in queue order. sessionId narrows the summary to one
// session's jobs; `ahead` then counts other sessions' unfinished jobs that
// sit before this session's last waiting job, i.e. work the queue does first.
export function summarizeQueue(jobs, { sessionId = null, now = Date.now() / 1000 } = {}) {
    const all = jobs || []
    const mine = sessionId == null ? all : all.filter((j) => j.session_id === sessionId)
    const byState = (s) => mine.filter((j) => j.state === s)
    const done = byState("done")
    const running = byState("running")
    const queued = byState("queued")
    const errors = byState("error")
    const total = mine.length
    const finished = done.length + errors.length
    const active = running.length + queued.length

    const fallbackAvg = mean(
        done.filter((j) => j.started_at != null && j.finished_at != null).map((j) => j.finished_at - j.started_at),
    )
    let eta = null
    if (active > 0) {
        const lanes = ["gpu", "coding"].map((l) => laneRemaining(mine, l, now, fallbackAvg))
        eta = lanes.some((x) => x === null) ? null : Math.max(...lanes)
    }

    let ahead = 0
    if (sessionId != null && queued.length) {
        const lastWaiting = all.lastIndexOf(queued[queued.length - 1])
        ahead = all.filter(
            (j, i) => i < lastWaiting && j.session_id !== sessionId && (j.state === "queued" || j.state === "running"),
        ).length
    }

    // Grouped by session in queue order, for the expanded list.
    const groups = []
    for (const j of mine) {
        let g = groups.find((x) => x.id === j.session_id)
        if (!g) {
            g = { id: j.session_id, name: j.session_name, jobs: [] }
            groups.push(g)
        }
        g.jobs.push(j)
    }

    return {
        done, running, queued, errors, total, finished, active,
        pct: total ? Math.round((finished / total) * 100) : 0,
        eta, ahead, groups,
    }
}
