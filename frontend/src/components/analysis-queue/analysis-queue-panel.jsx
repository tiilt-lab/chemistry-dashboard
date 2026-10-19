// Analysis-queue panel: the post-hoc queue (transcription, naming, video,
// coding) as a progress card. The sessions list shows the whole queue;
// a session's overview shows that session's jobs and how much other work
// sits ahead of them. Pure arithmetic lives in queue-summary.js.
import { Fragment, useEffect, useState } from "react"
import { SessionService } from "../../services/session-service"
import { startPolling } from "../../globals"
import { StatusPill } from "../status-pill"
import { Chevron } from "@/Icons"
import { summarizeQueue, legLabel, fmtEta, fmtElapsed, fmtDuration } from "./queue-summary"

export const QUEUE_POLL_MS = 5000

// The global queue, polled; null until the first answer.
export function useAnalysisQueue(pollMs = QUEUE_POLL_MS) {
    const [jobs, setJobs] = useState(null)
    useEffect(
        () =>
            startPolling(async (signal) => {
                const r = await new SessionService().getGlobalPosthocQueue({ signal })
                if (r.status !== 200) return false
                setJobs(await r.json())
                return true
            }, pollMs),
        [pollMs],
    )
    return jobs
}

const TONE = { running: "orange", done: "teal", error: "danger", queued: "neutral" }

function jobTiming(j, now) {
    if (j.state === "running") return fmtElapsed(j.started_at != null ? now - j.started_at : null)
    if (j.state === "done") return j.started_at != null && j.finished_at != null ? fmtDuration(j.finished_at - j.started_at) : "done"
    if (j.state === "error") return "failed"
    return "waiting"
}

export function AnalysisQueuePanel({ jobs, sessionId = null, onOpenSession }) {
    const [expanded, setExpanded] = useState(false)
    const [now, setNow] = useState(() => Date.now() / 1000)
    const s = summarizeQueue(jobs, { sessionId, now })
    const ticking = s.running.length > 0
    useEffect(() => {
        // Elapsed times and the projection move while something runs.
        if (!ticking) return
        const t = setInterval(() => setNow(Date.now() / 1000), 1000)
        return () => clearInterval(t)
    }, [ticking])
    if (!jobs || s.total === 0) return null

    const countChip = (n, label, cls) =>
        n > 0 ? (
            <span className={"flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold " + cls}>
                {n} {label}
            </span>
        ) : null
    const where = (j) => (sessionId == null ? `${j.session_name} › ${j.device_name}` : j.device_name)

    return (
        <div className="mb-4 overflow-hidden rounded-xl border border-tiilt-line bg-white">
            <button
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                className="w-full cursor-pointer px-4 py-3 text-left transition hover:bg-tiilt-soft/30"
            >
                <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                    <span className="flex items-center gap-2 text-sm font-semibold text-tiilt-ink">
                        {s.active > 0 ? (
                            <span className="h-2 w-2 animate-pulse rounded-full bg-tiilt-orange" />
                        ) : s.errors.length > 0 ? (
                            <span className="h-2 w-2 rounded-full bg-tiilt-danger" />
                        ) : (
                            <span className="h-2 w-2 rounded-full bg-tiilt-teal" />
                        )}
                        Analysis queue
                    </span>
                    {countChip(s.done.length, "done", "bg-tiilt-teal/15 text-tiilt-teal-text")}
                    {countChip(s.running.length, "running", "bg-tiilt-orange/15 text-tiilt-orange-text")}
                    {countChip(s.queued.length, "queued", "bg-tiilt-line/40 text-tiilt-muted")}
                    {countChip(s.errors.length, s.errors.length === 1 ? "error" : "errors", "bg-tiilt-danger-soft text-tiilt-danger")}
                    {s.ahead > 0 ? (
                        <span className="text-[11px] text-tiilt-muted" title="The queue runs those first">
                            {s.ahead} {s.ahead === 1 ? "job" : "jobs"} from other sessions ahead
                        </span>
                    ) : null}
                    <span className="ml-auto flex items-center gap-2 text-sm whitespace-nowrap text-tiilt-muted">
                        {s.active > 0 ? (
                            s.eta != null ? (
                                <span title="Projected from the average duration of finished jobs, per lane">
                                    {fmtEta(s.eta)} left
                                </span>
                            ) : (
                                <span>estimating…</span>
                            )
                        ) : (
                            <span className="font-semibold text-tiilt-teal-text">Finished</span>
                        )}
                        <Chevron
                            direction="down"
                            size={14}
                            style={{
                                transform: expanded ? "rotate(180deg)" : "none",
                                transition: "transform 0.15s",
                            }}
                        />
                    </span>
                </span>
                <span className="mt-2.5 flex items-center gap-3">
                    <span className="h-2 grow overflow-hidden rounded-full bg-tiilt-line/40">
                        <span
                            className="block h-full rounded-full bg-tiilt transition-all duration-700"
                            style={{ width: `${s.pct}%` }}
                        />
                    </span>
                    <span className="flex-none font-ahamono text-xs font-semibold text-tiilt-ink tabular-nums">
                        {s.finished}/{s.total}
                    </span>
                </span>
                {s.running.map((j) => (
                    <span key={j.id ?? `${j.session_id}-${j.device_id}`} className="mt-1.5 block text-xs text-tiilt-muted">
                        Now running <span className="font-semibold text-tiilt-ink">{where(j)}</span>
                        {" · "}
                        {legLabel(j)}
                        {j.started_at != null ? (
                            <span className="font-ahamono tabular-nums"> · {fmtElapsed(now - j.started_at)}</span>
                        ) : null}
                    </span>
                ))}
            </button>
            {expanded ? (
                <div className="flex max-h-80 flex-col gap-3 overflow-y-auto border-t border-tiilt-line bg-tiilt-ground/40 px-4 py-3">
                    {s.errors.length > 0 ? (
                        <div className="rounded-lg bg-tiilt-danger-soft px-3 py-2 text-xs leading-relaxed text-tiilt-danger">
                            {s.errors.map((j) => (
                                <div key={j.id ?? `${j.session_id}-${j.device_id}`}>
                                    <span className="font-semibold">{where(j)}:</span> {j.error || "failed"}
                                </div>
                            ))}
                        </div>
                    ) : null}
                    {s.groups.map((g) => {
                        const gDone = g.jobs.filter((j) => j.state === "done").length
                        return (
                            <div key={g.id} className="rounded-lg border border-tiilt-line bg-white px-3 py-2">
                                {sessionId == null ? (
                                    <div className="mb-1.5 flex items-baseline justify-between gap-2">
                                        <button
                                            onClick={() => onOpenSession && onOpenSession(g.id)}
                                            className="cursor-pointer text-xs font-semibold text-tiilt hover:underline"
                                        >
                                            {g.name} ›
                                        </button>
                                        <span className="font-ahamono text-[11px] text-tiilt-muted tabular-nums">
                                            {gDone}/{g.jobs.length}
                                        </span>
                                    </div>
                                ) : null}
                                <div className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1 text-xs">
                                    {g.jobs.map((j) => (
                                        <Fragment key={j.id ?? `${j.session_id}-${j.device_id}-${j.state}`}>
                                            <StatusPill
                                                tone={TONE[j.state] || "neutral"}
                                                pulse={j.state === "running"}
                                                className="text-[11px]"
                                                title={j.state === "error" ? j.error || "Failed" : undefined}
                                            >
                                                {j.device_name}
                                            </StatusPill>
                                            <span className="truncate text-tiilt-muted">{legLabel(j)}</span>
                                            <span className="font-ahamono text-[11px] text-tiilt-muted tabular-nums">
                                                {jobTiming(j, now)}
                                            </span>
                                        </Fragment>
                                    ))}
                                </div>
                            </div>
                        )
                    })}
                </div>
            ) : null}
        </div>
    )
}
