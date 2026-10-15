import { useEffect, useState } from "react"
import { ApiService } from "../services/api-service"
import { startPolling } from "../globals"
import { fmtUptime, fmtGb, cpuPercent, healthVerdict } from "./health-format"

// The server-health numbers we used to SSH in for, as one panel shared by
// Admin > Server health and the session page's Server load tab. Polls
// /api/v1/health every 5 s while enabled; backs off when it fails.
const POLL_MS = 5000

export function useHealth(enabled) {
    const [health, setHealth] = useState(null)
    const [error, setError] = useState(false)
    useEffect(() => {
        if (!enabled) return undefined
        return startPolling(async () => {
            try {
                const r = await new ApiService().httpRequestCall("api/v1/health", "GET", {})
                if (r.status !== 200) {
                    setError(true)
                    return false
                }
                setHealth(await r.json())
                setError(false)
                return true
            } catch {
                setError(true)
                return false
            }
        }, POLL_MS)
    }, [enabled])
    return { health, error }
}

function Bar({ pct, warn = 80, danger = 92 }) {
    const tone = pct >= danger ? "bg-red-500" : pct >= warn ? "bg-tiilt-orange" : "bg-tiilt-teal"
    return (
        <div className="h-2 w-full overflow-hidden rounded bg-tiilt-ground">
            <div className={`h-full rounded ${tone}`} style={{ width: `${Math.min(100, pct || 0)}%` }} />
        </div>
    )
}

function Metric({ label, value, pct, sub }) {
    return (
        <div className="rounded-xl border border-tiilt-line bg-white p-4">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">{label}</div>
            <div className="mt-1 text-2xl font-bold text-tiilt-ink">{value}</div>
            {pct != null && (
                <div className="mt-2">
                    <Bar pct={pct} />
                </div>
            )}
            {sub && <div className="mt-1 text-xs text-tiilt-muted">{sub}</div>}
        </div>
    )
}

const VERDICT_CLASS = {
    teal: "border-tiilt-teal/40 bg-tiilt-teal/10 text-tiilt-teal-text",
    orange: "border-tiilt-orange/40 bg-tiilt-orange/10 text-tiilt-orange-text",
    danger: "border-tiilt-danger/40 bg-tiilt-danger-soft text-tiilt-danger",
}

export function HealthPanel({ health: h, error }) {
    const verdict = healthVerdict(h)
    const cpu = cpuPercent(h && h.cpu)
    return (
        <div className="flex flex-col gap-4">
            {error && (
                <div className="rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger">
                    Couldn&apos;t reach the health endpoint; retrying.
                </div>
            )}
            {!h ? (
                <div className="py-10 text-center text-sm text-tiilt-muted">Loading…</div>
            ) : (
                <>
                    {verdict ? (
                        <div className={"rounded-lg border px-3 py-2 text-sm font-semibold " + VERDICT_CLASS[verdict.tone]}>{verdict.text}</div>
                    ) : null}
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                        <Metric
                            label="CPU load"
                            value={cpu != null ? `${cpu}%` : "—"}
                            pct={cpu}
                            sub={h.cpu && `${h.cpu.load_1} on ${h.cpu.cores} cores · 5 min ${h.cpu.load_5}`}
                        />
                        <Metric
                            label="GPU memory"
                            value={h.gpu ? `${h.gpu.mem_pct}%` : "—"}
                            pct={h.gpu && h.gpu.mem_pct}
                            sub={h.gpu && `${fmtGb(h.gpu.mem_used_mb, h.gpu.mem_total_mb)} · ${h.gpu.util_pct}% util`}
                        />
                        <Metric
                            label="Host RAM"
                            value={h.host_ram ? `${h.host_ram.used_pct}%` : "—"}
                            pct={h.host_ram && h.host_ram.used_pct}
                            sub={h.host_ram && `${h.host_ram.available_gb} GB free`}
                        />
                        <Metric
                            label="Disk"
                            value={h.disk ? `${h.disk.used_pct}%` : "—"}
                            pct={h.disk && h.disk.used_pct}
                            sub={h.disk && `${h.disk.free_gb} GB free`}
                        />
                        <Metric
                            label="Live pods"
                            value={h.live ? h.live.connected_devices : "—"}
                            sub={h.live && `${h.live.active_sessions} active session(s)`}
                        />
                    </div>

                    <div className="rounded-xl border border-tiilt-line bg-white p-4">
                        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">Post-hoc queue</div>
                        <div className="flex gap-6 text-sm text-tiilt-ink">
                            <span>{(h.posthoc_queue && h.posthoc_queue.running) || 0} running</span>
                            <span>{(h.posthoc_queue && h.posthoc_queue.queued) || 0} queued</span>
                            <span className={h.posthoc_queue && h.posthoc_queue.error ? "text-tiilt-danger" : ""}>
                                {(h.posthoc_queue && h.posthoc_queue.error) || 0} error
                            </span>
                        </div>
                    </div>

                    <div className="rounded-xl border border-tiilt-line bg-white p-4">
                        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">Services</div>
                        <div className="flex flex-col gap-1.5">
                            {Object.entries(h.services || {}).map(([name, s]) => (
                                <div key={name} className="flex items-center justify-between text-sm">
                                    <span className="flex items-center gap-2 text-tiilt-ink">
                                        <span className={`h-2 w-2 rounded-full ${s.active === "active" ? "bg-tiilt-teal" : "bg-red-500"}`} />
                                        {name}
                                    </span>
                                    <span className="font-ahamono text-xs text-tiilt-muted">
                                        {s.active} · up {fmtUptime(s.uptime_s)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="text-right text-[11px] text-tiilt-muted">updated {h.server_time} · refreshes every 5s</div>
                </>
            )}
        </div>
    )
}
