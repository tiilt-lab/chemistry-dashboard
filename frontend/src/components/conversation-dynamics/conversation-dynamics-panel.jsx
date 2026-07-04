import { useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"

// Palette matches the transcript / video-analytics speaker colors.
const COLORS = [
    "#3a2163",
    "#00a79d",
    "#c0007a",
    "#b26a00",
    "#4d7c1f",
    "#2e3192",
    "#b3261e",
]

// Per-speaker speaking-time equity + a who-follows-whom response network,
// derived from the pod's diarized transcript.
export function ConversationDynamicsPanel({ sessionId, sessionDeviceId }) {
    const [data, setData] = useState(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        if (!sessionId || !sessionDeviceId) return
        let alive = true
        new ApiService()
            .httpRequestCall(
                `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/dynamics`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
            .then((d) => alive && setData(d))
            .catch(() => alive && setError(true))
        return () => {
            alive = false
        }
    }, [sessionId, sessionDeviceId])

    if (error)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Couldn't load conversation dynamics.
            </div>
        )
    if (!data)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Loading…
            </div>
        )
    if (!data.speakers.length)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                No diarized speech to analyze in this pod.
            </div>
        )

    const idx = {}
    data.speakers.forEach((s, i) => (idx[s.name] = i))
    const colorOf = (name) => COLORS[(idx[name] ?? 0) % COLORS.length]
    const balance =
        data.gini <= 0.2
            ? "well balanced"
            : data.gini <= 0.4
              ? "somewhat uneven"
              : "dominated by a few speakers"

    return (
        <div className="flex w-full flex-col gap-6">
            <div>
                <div className="font-ahamono mb-1 text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Speaking balance
                </div>
                <div className="mb-3 text-xs text-tiilt-muted">
                    Participation is {balance} (Gini {data.gini}) ·{" "}
                    {data.total_turns} turns total
                </div>
                <div className="flex flex-col gap-1.5">
                    {data.speakers.map((s) => (
                        <div
                            key={s.name}
                            className="flex items-center gap-2 text-xs"
                        >
                            <span
                                className="w-24 flex-none truncate text-tiilt-ink"
                                title={s.name}
                            >
                                {s.name}
                            </span>
                            <div className="h-3 grow overflow-hidden rounded bg-tiilt-ground">
                                <div
                                    className="h-full rounded"
                                    style={{
                                        width: `${Math.max(2, s.share * 100)}%`,
                                        backgroundColor: colorOf(s.name),
                                    }}
                                />
                            </div>
                            <span className="w-28 flex-none text-right font-ahamono tabular-nums text-tiilt-muted">
                                {Math.round(s.share * 100)}% · {s.turns} turns
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            <div>
                <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Who responds to whom
                </div>
                {data.transitions.length ? (
                    <ul className="flex flex-col gap-1.5 text-xs">
                        {data.transitions.slice(0, 8).map((t, i) => (
                            <li key={i} className="flex items-center gap-2">
                                <span
                                    className="flex-none rounded px-1.5 py-0.5 font-semibold text-white"
                                    style={{ backgroundColor: colorOf(t.from) }}
                                >
                                    {t.from}
                                </span>
                                <span className="text-tiilt-muted">→</span>
                                <span
                                    className="flex-none rounded px-1.5 py-0.5 font-semibold text-white"
                                    style={{ backgroundColor: colorOf(t.to) }}
                                >
                                    {t.to}
                                </span>
                                <span className="text-tiilt-muted">
                                    {t.count}×
                                </span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <div className="text-xs text-tiilt-muted">
                        Not enough turns to build a response network.
                    </div>
                )}
            </div>
        </div>
    )
}
