import { useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"

// A student's per-session participation across the term. Each bar carries a
// fair-share tick (1/group size) so over/under-participation reads at a
// glance; the header flags the direction of travel.

// "up" / "down" only for a monotonic run over the last three sessions —
// anything noisier is "flat" rather than a false alarm.
export const trendOf = (values) => {
    if (!values || values.length < 3) return null
    const [a, b, c] = values.slice(-3)
    if (c > b && b > a) return "up"
    if (c < b && b < a) return "down"
    return "flat"
}

// seconds -> "m:ss" (talk time is minutes-scale, not hours)
export const fmtMins = (sec) => {
    const s = Math.max(0, Math.round(sec || 0))
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}

// Open-question ratio per session (only sessions where they asked any).
export const openRatios = (rows) =>
    rows
        .filter((r) => (r.questions || 0) > 0)
        .map((r) => Math.round((100 * (r.open_questions || 0)) / r.questions))

// Idea give-and-take rows (only sessions with a stored post-hoc report).
// Both metrics share one normalization max so "gives" and "takes" bars are
// comparable with each other — they're the two directions of the same
// cross-cohesion measure.
export const giveTake = (rows) => {
    const withPair = rows.filter(
        (r) => r.influence != null || r.external_relevance != null,
    )
    const max = Math.max(
        0,
        ...withPair.flatMap((r) => [r.influence || 0, r.external_relevance || 0]),
    )
    return {
        rows: withPair,
        norm: (v) => (max > 0 && v != null ? Math.max(2, (v / max) * 100) : 0),
    }
}

const TREND_CHIP = {
    up: { text: "▲ growing", cls: "bg-tiilt-teal/15 text-tiilt-teal-text" },
    down: { text: "▼ declining", cls: "bg-tiilt-orange/15 text-tiilt-orange-text" },
    flat: { text: "steady", cls: "bg-tiilt-line/40 text-tiilt-muted" },
}

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

    const trend = trendOf(withData.map((r) => r.speaking_share))
    const chip = trend ? TREND_CHIP[trend] : null

    // Term averages for the footer.
    const avgTurns = Math.round(
        withData.reduce((s, r) => s + (r.turns || 0), 0) / withData.length,
    )
    const turnSecs = withData
        .filter((r) => r.avg_turn_seconds != null)
        .map((r) => r.avg_turn_seconds)
    const avgTurnLen = turnSecs.length
        ? Math.round(turnSecs.reduce((s, v) => s + v, 0) / turnSecs.length)
        : null
    const ratios = openRatios(withData)
    const ratioTrend = trendOf(ratios)

    return (
        <div className="flex w-full flex-col gap-2">
            <div className="flex items-center gap-2">
                <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Participation across sessions
                </div>
                {chip ? (
                    <span
                        className={
                            "rounded-full px-2 py-0.5 text-[11px] font-semibold " +
                            chip.cls
                        }
                        title="Speaking-share direction over the last three sessions"
                    >
                        {chip.text}
                    </span>
                ) : null}
            </div>
            <div className="flex flex-col gap-1.5">
                {withData.map((r) => {
                    const fairPct = r.group_size
                        ? Math.round(100 / r.group_size)
                        : null
                    return (
                        <div
                            key={r.session_id}
                            className="flex items-center gap-2 text-xs"
                        >
                            <span
                                className="w-36 flex-none truncate text-tiilt-ink"
                                title={`${r.session_name} · ${r.date ? r.date.slice(0, 10) : ""} · ${r.turns || 0} turns`}
                            >
                                {r.session_name || `Session ${r.session_id}`}
                            </span>
                            <div className="relative h-3 grow overflow-hidden rounded bg-tiilt-ground">
                                <div
                                    className="h-full rounded bg-tiilt"
                                    style={{
                                        width: `${Math.max(2, r.speaking_share * 100)}%`,
                                    }}
                                />
                                {fairPct != null ? (
                                    <div
                                        className="absolute top-0 h-full w-px bg-tiilt-orange"
                                        style={{ left: `${fairPct}%` }}
                                        title={`Fair share for ${r.group_size} speakers: ${fairPct}%`}
                                    />
                                ) : null}
                            </div>
                            <span className="w-10 flex-none text-right font-ahamono tabular-nums text-tiilt-muted">
                                {Math.round(r.speaking_share * 100)}%
                            </span>
                            <span
                                className="w-11 flex-none text-right font-ahamono tabular-nums text-tiilt-muted"
                                title="Minutes of speech"
                            >
                                {fmtMins(r.speaking_seconds)}
                            </span>
                            <span
                                className="w-9 flex-none text-right font-ahamono tabular-nums text-tiilt-muted"
                                title={`Rank among ${r.group_size} speakers by talk time`}
                            >
                                {r.rank ? `${r.rank}/${r.group_size}` : "—"}
                            </span>
                            <span
                                className="w-14 flex-none text-right font-ahamono tabular-nums text-tiilt-muted"
                                title="Questions asked (open questions in parentheses)"
                            >
                                {r.questions != null
                                    ? `${r.questions}q${r.open_questions ? ` (${r.open_questions})` : ""}`
                                    : ""}
                            </span>
                        </div>
                    )
                })}
            </div>
            {(() => {
                const gt = giveTake(withData)
                if (!gt.rows.length) return null
                const inflTrend = trendOf(
                    gt.rows.map((r) => r.influence).filter((v) => v != null),
                )
                return (
                    <div className="mt-2 flex flex-col gap-1.5">
                        <div className="flex items-center gap-2">
                            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Idea give-and-take
                            </div>
                            {inflTrend === "up" ? (
                                <span className="rounded-full bg-tiilt-teal/15 px-2 py-0.5 text-[11px] font-semibold text-tiilt-teal-text">
                                    ▲ influence growing
                                </span>
                            ) : inflTrend === "down" ? (
                                <span className="rounded-full bg-tiilt-orange/15 px-2 py-0.5 text-[11px] font-semibold text-tiilt-orange-text">
                                    ▼ influence declining
                                </span>
                            ) : null}
                        </div>
                        {gt.rows.map((r) => (
                            <div
                                key={r.session_id}
                                className="flex items-center gap-2 text-xs"
                            >
                                <span className="w-36 flex-none truncate text-tiilt-ink">
                                    {r.session_name || `Session ${r.session_id}`}
                                </span>
                                <div className="flex grow flex-col gap-0.5">
                                    <div
                                        className="h-1.5 rounded bg-tiilt-teal/70"
                                        style={{ width: `${gt.norm(r.influence)}%` }}
                                        title={`Influence ${r.influence ?? "—"}: how much others' following speech relates to theirs`}
                                    />
                                    <div
                                        className="h-1.5 rounded bg-tiilt-lavender"
                                        style={{ width: `${gt.norm(r.external_relevance)}%` }}
                                        title={`External relevance ${r.external_relevance ?? "—"}: how much their speech relates to others'`}
                                    />
                                </div>
                            </div>
                        ))}
                        <div className="text-[11px] text-tiilt-muted">
                            <span className="font-semibold text-tiilt-teal-text">
                                Teal
                            </span>{" "}
                            = influence (others take up their ideas);{" "}
                            <span className="font-semibold text-tiilt">
                                lavender
                            </span>{" "}
                            = relevance (they build on others'). Read as a
                            pair — introducers run teal-heavy, synthesizers
                            lavender-heavy. Only sessions with a full
                            post-hoc analysis appear.
                        </div>
                    </div>
                )
            })()}
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-tiilt-muted">
                <span>
                    Avg {avgTurns} {avgTurns === 1 ? "turn" : "turns"}/session
                    {avgTurnLen != null ? ` · ~${avgTurnLen}s per turn` : ""}
                </span>
                {ratios.length >= 2 ? (
                    <span title="Share of their questions that were open-ended, per session">
                        Open-question ratio: {ratios.slice(-3).join("% → ")}%
                        {ratioTrend === "up"
                            ? " ▲"
                            : ratioTrend === "down"
                              ? " ▼"
                              : ""}
                    </span>
                ) : null}
            </div>
            <div className="text-[11px] text-tiilt-muted">
                Bars are share of group speaking time (
                <span className="text-tiilt-orange">|</span> marks the fair
                share for the group's size); then minutes spoken, rank in
                group, and questions asked (open in parentheses).
            </div>
        </div>
    )
}
