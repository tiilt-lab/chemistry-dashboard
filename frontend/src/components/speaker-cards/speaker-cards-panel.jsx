import { useEffect, useState } from "react"
import { ApiService } from "../../services/api-service"
import { speakerColorFor } from "../../globals"

// "Who did what" — one card per speaker on the pod Group view: talk share and
// turns (from the dynamics endpoint) plus average GCA scores (from the
// transcripts already loaded). Clicking a card opens the per-speaker detail
// view, replacing the old dropdown-driven Individual Comparison entry point.
const PI_METRICS = [
    { key: "participation_score", short: "Part", name: "Participation" },
    { key: "social_impact", short: "Impact", name: "Social Impact" },
    { key: "responsivity", short: "Resp", name: "Responsivity" },
    { key: "internal_cohesion", short: "Cohes", name: "Internal Cohesion" },
    { key: "newness", short: "New", name: "Newness" },
]

function piAverages(transcripts, speakerId) {
    const sums = {}
    const counts = {}
    for (const t of transcripts || []) {
        const row = (t.speaker_metrics || []).find(
            (m) => m.speaker_id === speakerId,
        )
        if (!row) continue
        for (const m of PI_METRICS) {
            if (typeof row[m.key] !== "number") continue
            sums[m.key] = (sums[m.key] || 0) + row[m.key]
            counts[m.key] = (counts[m.key] || 0) + 1
        }
    }
    const out = {}
    for (const m of PI_METRICS)
        out[m.key] = counts[m.key]
            ? Math.round((sums[m.key] / counts[m.key]) * 100)
            : null
    return out
}

function SpeakerCardsPanel({
    sessionId,
    sessionDeviceId,
    speakers,
    transcripts,
    onOpenSpeaker,
}) {
    const [dynamics, setDynamics] = useState(null)

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
            .then((d) => alive && d && setDynamics(d))
            .catch(() => {})
        return () => { alive = false }
    }, [sessionId, sessionDeviceId])

    if (!speakers || speakers.length === 0)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                No speakers identified in this pod yet.
            </div>
        )

    const allAliases = speakers.map((s) => s.alias)
    const talkOf = (alias) =>
        ((dynamics && dynamics.speakers) || []).find((d) => d.name === alias)

    return (
        <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            {speakers.map((speaker) => {
                const color = speakerColorFor(speaker.alias, allAliases)
                const talk = talkOf(speaker.alias)
                const averages = piAverages(transcripts, speaker.id)
                const card = (
                    <>
                        <div className="flex items-center justify-between gap-2">
                            <span className="flex min-w-0 items-center gap-2">
                                <span
                                    className="h-2.5 w-2.5 flex-none rounded-full"
                                    style={{ backgroundColor: color }}
                                />
                                <span className="truncate text-sm font-semibold text-tiilt-ink">
                                    {speaker.alias}
                                </span>
                            </span>
                            {onOpenSpeaker && (
                                <span className="flex-none text-xs text-tiilt-muted">
                                    details ›
                                </span>
                            )}
                        </div>
                        <div className="mt-2 flex items-center gap-2">
                            <div className="h-2.5 grow overflow-hidden rounded bg-tiilt-ground">
                                <div
                                    className="h-full rounded"
                                    style={{
                                        width: `${Math.max(2, (talk ? talk.share : 0) * 100)}%`,
                                        backgroundColor: color,
                                    }}
                                />
                            </div>
                            <span className="flex-none font-ahamono text-[11px] tabular-nums text-tiilt-muted">
                                {talk
                                    ? `${Math.round(talk.share * 100)}% · ${talk.turns} turns`
                                    : "no talk data"}
                            </span>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                            {PI_METRICS.map((m) => (
                                <span
                                    key={m.key}
                                    className="flex items-baseline gap-1"
                                    title={m.name}
                                >
                                    <span className="font-ahamono text-[10px] tracking-wider text-tiilt-muted uppercase">
                                        {m.short}
                                    </span>
                                    <span className="text-xs font-semibold text-tiilt-ink tabular-nums">
                                        {averages[m.key] == null
                                            ? "—"
                                            : averages[m.key]}
                                    </span>
                                </span>
                            ))}
                        </div>
                    </>
                )
                return onOpenSpeaker ? (
                    <button
                        key={speaker.id}
                        type="button"
                        onClick={() =>
                            onOpenSpeaker(speaker.id, speaker.alias)
                        }
                        className="rounded-lg border border-tiilt-line bg-white p-3 text-left transition hover:border-tiilt hover:bg-tiilt-soft/40"
                    >
                        {card}
                    </button>
                ) : (
                    <div
                        key={speaker.id}
                        className="rounded-lg border border-tiilt-line bg-white p-3"
                    >
                        {card}
                    </div>
                )
            })}
        </div>
    )
}

export { SpeakerCardsPanel }
