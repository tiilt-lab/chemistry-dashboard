import { useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"

// A student's per-session speaking share (+ attention) across the term, so you
// can see participation grow (or fade) over time.
export function StudentLongitudinalPanel({ username }) {
    const [rows, setRows] = useState(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        if (!username) return
        let alive = true
        new ApiService()
            .httpRequestCall(
                `api/v1/students/${encodeURIComponent(username)}/longitudinal`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
            .then((d) => alive && setRows(d))
            .catch(() => alive && setError(true))
        return () => {
            alive = false
        }
    }, [username])

    if (error)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Couldn't load session history.
            </div>
        )
    if (!rows)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Loading…
            </div>
        )
    const withData = rows.filter((r) => r.speaking_seconds > 0)
    if (!withData.length)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                No participation recorded yet.
            </div>
        )

    return (
        <div className="flex w-full flex-col gap-2">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                Participation across sessions
            </div>
            <div className="flex flex-col gap-1.5">
                {withData.map((r) => (
                    <div
                        key={r.session_id}
                        className="flex items-center gap-2 text-xs"
                    >
                        <span
                            className="w-40 flex-none truncate text-tiilt-ink"
                            title={`${r.session_name} · ${r.date ? r.date.slice(0, 10) : ""}`}
                        >
                            {r.session_name || `Session ${r.session_id}`}
                        </span>
                        <div className="h-3 grow overflow-hidden rounded bg-tiilt-ground">
                            <div
                                className="h-full rounded bg-tiilt"
                                style={{
                                    width: `${Math.max(2, r.speaking_share * 100)}%`,
                                }}
                            />
                        </div>
                        <span className="w-16 flex-none text-right font-ahamono tabular-nums text-tiilt-muted">
                            {Math.round(r.speaking_share * 100)}%
                        </span>
                    </div>
                ))}
            </div>
            <div className="mt-1 text-[11px] text-tiilt-muted">
                Bars show this student's share of speaking time per session.
            </div>
        </div>
    )
}
