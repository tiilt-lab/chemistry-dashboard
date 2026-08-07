import { useEffect, useState } from "react"
import { ApiService } from "../../services/api-service"
import { formatHMS } from "../../globals"

// Joint visual attention: the share of tracked moments where >=2 members'
// gaze (Gaze-LLE point snapped to the nearest detected object) landed on the
// same target. This is the group-level gaze construct with the strongest
// evidence base in the collaboration-sensing literature.
const prettyTarget = (t) =>
    t && t.startsWith("person:") ? `${t.slice(7)} (person)` : t

function JointAttentionPanel({ sessionId, sessionDeviceId }) {
    const [data, setData] = useState(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        if (!sessionId || !sessionDeviceId) return
        // Guard against a slow response for a previous pod overwriting the
        // current pod's data after a quick switch.
        let alive = true
        new ApiService()
            .httpRequestCall(
                `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/joint_attention`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
            .then((d) => alive && setData(d))
            .catch(() => alive && setError(true))
        return () => { alive = false }
    }, [sessionId, sessionDeviceId])

    if (error)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Couldn't load joint attention.
            </div>
        )
    if (!data)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Loading…
            </div>
        )
    if (data.empty)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                Not enough gaze data — joint attention needs two or more
                tracked members on video.
            </div>
        )

    return (
        <div className="flex w-full flex-col gap-5">
            <div className="flex items-baseline gap-3">
                <span className="text-3xl font-bold text-tiilt-ink tabular-nums">
                    {Math.round(data.joint_share * 100)}%
                </span>
                <span className="text-xs leading-relaxed text-tiilt-muted">
                    of tracked moments had two or more members looking at the
                    same thing
                </span>
            </div>

            {data.timeline.length > 1 && (
                <div>
                    <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Shared focus over time
                    </div>
                    <div className="flex h-8 w-full items-end gap-px overflow-hidden rounded bg-tiilt-ground">
                        {data.timeline.map((b) => (
                            <div
                                key={b.start}
                                className="bg-tiilt-teal grow rounded-sm"
                                style={{
                                    height: `${Math.max(6, b.share * 100)}%`,
                                    opacity: 0.25 + 0.75 * b.share,
                                }}
                                title={`${formatHMS(b.start)} — ${Math.round(b.share * 100)}% shared focus`}
                            />
                        ))}
                    </div>
                </div>
            )}

            {data.top_targets.length > 0 && (
                <div>
                    <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Most-shared targets
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {data.top_targets.map((t) => (
                            <span
                                key={t.target}
                                className="rounded-full bg-tiilt-ground px-2.5 py-1 text-xs text-tiilt-ink"
                            >
                                {prettyTarget(t.target)}
                                <span className="ml-1.5 font-ahamono text-[10px] text-tiilt-muted">
                                    ×{t.moments}
                                </span>
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {(data.pairs.length > 0 || data.peer_gaze.length > 0) && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {data.pairs.length > 0 && (
                        <div>
                            <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Shared focus partners
                            </div>
                            <div className="flex flex-col gap-1 text-xs text-tiilt-ink">
                                {data.pairs.slice(0, 6).map((p) => (
                                    <span key={`${p.a}|${p.b}`}>
                                        {p.a} + {p.b}
                                        <span className="ml-1.5 font-ahamono text-[10px] text-tiilt-muted">
                                            {p.moments} moments
                                        </span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                    {data.peer_gaze.length > 0 && (
                        <div>
                            <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Looks toward
                            </div>
                            <div className="flex flex-col gap-1 text-xs text-tiilt-ink">
                                {data.peer_gaze.slice(0, 6).map((g) => (
                                    <span key={`${g.from}|${g.to}`}>
                                        {g.from} → {g.to}
                                        <span className="ml-1.5 font-ahamono text-[10px] text-tiilt-muted">
                                            {g.moments} moments
                                        </span>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export { JointAttentionPanel }
