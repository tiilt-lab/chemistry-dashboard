import { useEffect, useState } from "react"
import { ApiService } from "../../services/api-service"

// Slim at-a-glance strip at the top of the pod Group view: the numbers a
// teacher wants before deciding whether to scroll. Reuses the conversation
// dynamics endpoint rather than adding a new one.
function SessionVitals({ sessionId, sessionDeviceId }) {
    const [data, setData] = useState(null)

    useEffect(() => {
        if (!sessionId || !sessionDeviceId) return
        // Guard against a slow response for a previous pod overwriting the
        // current pod's data after a quick switch.
        let alive = true
        new ApiService()
            .httpRequestCall(
                `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/dynamics`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : null))
            .then((d) => alive && d && setData(d))
            .catch(() => {})
        return () => { alive = false }
    }, [sessionId, sessionDeviceId])

    if (!data || !data.speakers || data.speakers.length === 0) return null

    const minutes = Math.round((data.total_speaking_seconds || 0) / 60)
    const balance =
        data.gini <= 0.2
            ? "even"
            : data.gini <= 0.4
              ? "somewhat uneven"
              : "dominated by a few"

    const vitals = [
        { label: "speakers", value: data.speakers.length },
        { label: "turns", value: data.total_turns },
        { label: "min speaking", value: minutes },
        { label: "balance", value: balance },
    ]

    return (
        <div className="flex w-full flex-wrap items-baseline gap-x-5 gap-y-1 rounded-xl border border-tiilt-line bg-white px-4 py-2.5">
            {vitals.map((v) => (
                <span key={v.label} className="flex items-baseline gap-1.5">
                    <span className="text-sm font-bold text-tiilt-ink tabular-nums">
                        {v.value}
                    </span>
                    <span className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                        {v.label}
                    </span>
                </span>
            ))}
        </div>
    )
}

export { SessionVitals }
