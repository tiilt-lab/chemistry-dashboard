import { useEffect, useState } from "react"
import { ApiService } from "../services/api-service"
import { Appheader } from "../header/header-component"
import { useRequireManager } from "../routes/roles"

// One-screen server health for a live class: the GPU/RAM/disk/queue numbers
// we used to SSH in for. Polls /api/v1/health every 5s.
function Bar({ pct, warn = 80, danger = 92 }) {
    const tone =
        pct >= danger ? "bg-red-500" : pct >= warn ? "bg-tiilt-orange" : "bg-tiilt-teal"
    return (
        <div className="h-2 w-full overflow-hidden rounded bg-tiilt-ground">
            <div
                className={`h-full rounded ${tone}`}
                style={{ width: `${Math.min(100, pct || 0)}%` }}
            />
        </div>
    )
}

function Metric({ label, value, pct, sub }) {
    return (
        <div className="rounded-xl border border-tiilt-line bg-white p-4">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                {label}
            </div>
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

function fmtUptime(s) {
    if (s == null) return "—"
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export function OpsComponent(props) {
    // Server internals are admin territory; this page used to be reachable by
    // any signed-in account that knew the URL.
    const canView = useRequireManager(props.userdata)
    const [h, setH] = useState(null)
    const [err, setErr] = useState(false)
    useEffect(() => {
        if (!canView) return
        let alive = true
        const load = () =>
            new ApiService()
                .httpRequestCall("api/v1/health", "GET", {})
                .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
                .then((d) => alive && (setH(d), setErr(false)))
                .catch(() => alive && setErr(true))
        load()
        const t = setInterval(load, 5000)
        return () => {
            alive = false
            clearInterval(t)
        }
    }, [canView])

    return (
        <div role="main" className="main-container">
            <Appheader title="Server health" leftText={false} rightText={""} />
            <div className="mx-auto w-full max-w-3xl overflow-y-auto px-4 py-6">
                {err && (
                    <div className="mb-4 rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger">
                        Couldn't reach the health endpoint.
                    </div>
                )}
                {!h ? (
                    <div className="py-10 text-center text-sm text-tiilt-muted">
                        Loading…
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <Metric
                                label="GPU memory"
                                value={h.gpu ? `${h.gpu.mem_pct}%` : "—"}
                                pct={h.gpu?.mem_pct}
                                sub={h.gpu && `${(h.gpu.mem_used_mb / 1024).toFixed(1)} / ${(h.gpu.mem_total_mb / 1024).toFixed(0)} GB · ${h.gpu.util_pct}% util`}
                            />
                            <Metric
                                label="Host RAM"
                                value={h.host_ram ? `${h.host_ram.used_pct}%` : "—"}
                                pct={h.host_ram?.used_pct}
                                sub={h.host_ram && `${h.host_ram.available_gb} GB free`}
                            />
                            <Metric
                                label="Disk"
                                value={h.disk ? `${h.disk.used_pct}%` : "—"}
                                pct={h.disk?.used_pct}
                                sub={h.disk && `${h.disk.free_gb} GB free`}
                            />
                            <Metric
                                label="Live pods"
                                value={h.live ? h.live.connected_devices : "—"}
                                sub={h.live && `${h.live.active_sessions} active session(s)`}
                            />
                        </div>

                        <div className="rounded-xl border border-tiilt-line bg-white p-4">
                            <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Post-hoc queue
                            </div>
                            <div className="flex gap-6 text-sm text-tiilt-ink">
                                <span>{h.posthoc_queue?.running ?? 0} running</span>
                                <span>{h.posthoc_queue?.queued ?? 0} queued</span>
                                <span className={h.posthoc_queue?.error ? "text-tiilt-danger" : ""}>
                                    {h.posthoc_queue?.error ?? 0} error
                                </span>
                            </div>
                        </div>

                        <div className="rounded-xl border border-tiilt-line bg-white p-4">
                            <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Services
                            </div>
                            <div className="flex flex-col gap-1.5">
                                {Object.entries(h.services || {}).map(([name, s]) => (
                                    <div key={name} className="flex items-center justify-between text-sm">
                                        <span className="flex items-center gap-2 text-tiilt-ink">
                                            <span
                                                className={`h-2 w-2 rounded-full ${s.active === "active" ? "bg-tiilt-teal" : "bg-red-500"}`}
                                            />
                                            {name}
                                        </span>
                                        <span className="font-ahamono text-xs text-tiilt-muted">
                                            {s.active} · up {fmtUptime(s.uptime_s)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="text-right text-[11px] text-tiilt-muted">
                            updated {h.server_time} · refreshes every 5s
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
