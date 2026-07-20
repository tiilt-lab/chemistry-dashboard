import { useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"
import { speakerColorFor } from "../../globals"
import { useIsDark } from "../../myhooks/custom-hooks"
import { fmtClock } from "../../lib/utils"



// Directed response network: speakers on a circle, curved arrows weighted by
// how often the source speaker follows the target. Pure SVG; colors resolve
// from the theme-aware speaker palette and CSS vars.
function ResponseGraph({ transitions, colorOf, sharesByName }) {
    const shown = transitions
        .filter((t) => t.from !== t.to)
        .slice(0, 12)
    const names = [...new Set(shown.flatMap((t) => [t.from, t.to]))]
    if (!names.length) return null

    const W = 440
    const H = Math.max(240, 190 + names.length * 14)
    const cx = W / 2
    const cy = H / 2
    const R = Math.min(W, H) / 2 - 52
    // Node size encodes speaking-time share (relative to the loudest shown).
    const maxShare = Math.max(
        ...names.map((n) => (sharesByName && sharesByName[n]) || 0),
        0.0001,
    )
    const radiusOf = (n) =>
        9 + 11 * (((sharesByName && sharesByName[n]) || 0) / maxShare)
    const pos = {}
    names.forEach((n, i) => {
        const a = (2 * Math.PI * i) / names.length - Math.PI / 2
        pos[n] = { x: cx + R * Math.cos(a), y: cy + R * Math.sin(a), a }
    })
    const maxCount = Math.max(...shown.map((t) => t.count))

    const edges = shown.map((t) => {
        const p0 = pos[t.from]
        const p1 = pos[t.to]
        const dx = p1.x - p0.x
        const dy = p1.y - p0.y
        const len = Math.hypot(dx, dy) || 1
        const ux = dx / len
        const uy = dy / len
        const px = -uy // perpendicular, left of travel: A->B and B->A bow apart
        const py = ux
        const bow = Math.min(36, len * 0.22)
        const r0 = radiusOf(t.from)
        const r1 = radiusOf(t.to)
        const sx = p0.x + ux * (r0 + 3)
        const sy = p0.y + uy * (r0 + 3)
        const ex = p1.x - ux * (r1 + 8)
        const ey = p1.y - uy * (r1 + 8)
        const mx = (sx + ex) / 2 + px * bow
        const my = (sy + ey) / 2 + py * bow
        // Arrowhead aligned with the curve's direction at its end.
        const adx = ex - mx
        const ady = ey - my
        const alen = Math.hypot(adx, ady) || 1
        const ax = adx / alen
        const ay = ady / alen
        const apx = -ay
        const apy = ax
        const ah = 7 + 3 * (t.count / maxCount)
        const arrow = `${ex + ax * ah},${ey + ay * ah} ${ex + apx * ah * 0.55},${ey + apy * ah * 0.55} ${ex - apx * ah * 0.55},${ey - apy * ah * 0.55}`
        return {
            key: `${t.from}->${t.to}`,
            d: `M ${sx} ${sy} Q ${mx} ${my} ${ex} ${ey}`,
            width: 1.5 + 4.5 * (t.count / maxCount),
            color: colorOf(t.from),
            arrow,
            label: {
                x: 0.25 * sx + 0.5 * mx + 0.25 * ex,
                y: 0.25 * sy + 0.5 * my + 0.25 * ey,
            },
            count: t.count,
            title: `${t.from} responds to ${t.to} \u00d7${t.count}`,
        }
    })

    const labelFor = (n) => {
        const p = pos[n]
        const off = R + radiusOf(n) + 12
        const lx = cx + off * Math.cos(p.a)
        const ly = cy + off * Math.sin(p.a)
        const anchor =
            Math.cos(p.a) > 0.25 ? "start" : Math.cos(p.a) < -0.25 ? "end" : "middle"
        return { lx, ly, anchor }
    }

    return (
        <svg
            viewBox={`0 0 ${W} ${H}`}
            className="w-full max-w-xl"
            role="img"
            aria-label="Response network: arrows point from a speaker to the person they respond to, thicker arrows mean more responses"
        >
            {edges.map((e) => (
                <g key={e.key}>
                    <title>{e.title}</title>
                    <path
                        d={e.d}
                        fill="none"
                        stroke={e.color}
                        strokeWidth={e.width}
                        strokeLinecap="round"
                        opacity="0.7"
                    />
                    <polygon points={e.arrow} fill={e.color} opacity="0.85" />
                </g>
            ))}
            {edges.map((e) => (
                <text
                    key={e.key + "-label"}
                    x={e.label.x}
                    y={e.label.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="11"
                    fontWeight="700"
                    style={{
                        fill: "var(--color-tiilt-ink)",
                        stroke: "var(--color-white)",
                        strokeWidth: 3,
                        paintOrder: "stroke",
                    }}
                >
                    {e.count}
                </text>
            ))}
            {names.map((n) => (
                <g key={n}>
                    <title>
                        {sharesByName && sharesByName[n] != null
                            ? `${n} \u2014 ${Math.round(sharesByName[n] * 100)}% of speaking time`
                            : n}
                    </title>
                    <circle
                        cx={pos[n].x}
                        cy={pos[n].y}
                        r={radiusOf(n)}
                        fill={colorOf(n)}
                        stroke="var(--color-white)"
                        strokeWidth="2.5"
                    />
                </g>
            ))}
            {names.map((n) => {
                const { lx, ly, anchor } = labelFor(n)
                return (
                    <text
                        key={n + "-name"}
                        x={lx}
                        y={ly}
                        textAnchor={anchor}
                        dominantBaseline="middle"
                        fontSize="12"
                        fontWeight="600"
                        style={{ fill: "var(--color-tiilt-ink)" }}
                    >
                        {n.length > 14 ? n.slice(0, 13) + "\u2026" : n}
                    </text>
                )
            })}
        </svg>
    )
}


function Stat({ label, value, title }) {
    return (
        <div
            className="rounded-lg border border-tiilt-line bg-tiilt-ground/50 px-3 py-2"
            title={title}
        >
            <div className="text-base font-bold text-tiilt-ink">{value}</div>
            <div className="text-[11px] text-tiilt-muted">{label}</div>
        </div>
    )
}

// Stacked columns: one per time bucket, colored by speaker; unfilled column
// height is silence — so quiet stretches are visible at a glance.
function EquityTimeline({ timeline, colorOf }) {
    const { buckets, bucket_seconds } = timeline
    if (!buckets || !buckets.length) return null
    return (
        <div>
            <div className="flex h-20 items-end gap-1">
                {buckets.map((b, i) => {
                    const total = Object.values(b).reduce((a, v) => a + v, 0)
                    const fill = Math.min(1, total / bucket_seconds)
                    return (
                        <div
                            key={i}
                            className="flex grow flex-col-reverse overflow-hidden rounded-sm bg-tiilt-ground"
                            style={{ height: "100%" }}
                            title={`${fmtClock(i * bucket_seconds)}–${fmtClock((i + 1) * bucket_seconds)} · ${Math.round(fill * 100)}% talk`}
                        >
                            {Object.entries(b)
                                .sort((x, y) => y[1] - x[1])
                                .map(([name, sec]) => (
                                    <div
                                        key={name}
                                        style={{
                                            height: `${(sec / bucket_seconds) * 100}%`,
                                            backgroundColor: colorOf(name),
                                        }}
                                        title={`${name}: ${Math.round(sec)}s`}
                                    />
                                ))}
                        </div>
                    )
                })}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-tiilt-muted">
                <span>start</span>
                <span>
                    {fmtClock(buckets.length * bucket_seconds)} · empty space =
                    silence
                </span>
            </div>
        </div>
    )
}

// Per-speaker speaking-time equity + a who-follows-whom response network,
// derived from the pod's diarized transcript.
export function ConversationDynamicsPanel({ sessionId, sessionDeviceId }) {
    useIsDark() // re-render on theme toggle: speaker colors resolve per-theme
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

    const talk = data.talk
    // Include timeline-only names (e.g. "Unattributed") in the palette space.
    const allNames = [
        ...new Set([
            ...data.speakers.map((s) => s.name),
            ...(talk && talk.per_speaker
                ? talk.per_speaker.map((s) => s.name)
                : []),
        ]),
    ]
    const colorOf = (name) => speakerColorFor(name, allNames)
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

            {talk && !talk.empty && (
                <>
                    {talk.never_spoke && talk.never_spoke.length > 0 && (
                        <div className="rounded-md bg-tiilt-orange/15 px-3 py-2 text-xs leading-relaxed text-tiilt-orange-text">
                            Never spoke (or no utterance was attributed to
                            them): {talk.never_spoke.join(", ")}
                        </div>
                    )}

                    <div>
                        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                            Participation over time
                        </div>
                        <EquityTimeline
                            timeline={talk.timeline}
                            colorOf={colorOf}
                        />
                    </div>

                    <div>
                        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                            Silence &amp; turn-taking
                        </div>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            <Stat
                                label={`silences over ${Math.round(talk.silences.threshold_seconds)}s`}
                                value={talk.silences.count}
                                title={`${talk.silences.pct_of_session}% of the session was silent`}
                            />
                            <Stat
                                label="longest silence"
                                value={
                                    talk.silences.longest
                                        ? fmtClock(talk.silences.longest.seconds)
                                        : "—"
                                }
                                title={
                                    talk.silences.longest
                                        ? `at ${fmtClock(talk.silences.longest.at)} into the session`
                                        : undefined
                                }
                            />
                            <Stat
                                label="clean handoffs"
                                value={talk.turn_taking.clean_handoffs}
                                title="Speaker changes with no overlap"
                            />
                            <Stat
                                label="interruptions"
                                value={talk.turn_taking.interruptions}
                                title="Speaker changes that overlapped the previous speaker by more than 1s"
                            />
                        </div>
                    </div>

                    <div>
                        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                            Questions
                        </div>
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            <Stat label="questions asked" value={talk.questions.total} />
                            <Stat
                                label="open / closed"
                                value={`${talk.questions.open} / ${talk.questions.closed}`}
                                title="Heuristic on the question's first words: why/how/what-if count as open; yes-no starters as closed. The rest are unclassified."
                            />
                            <Stat
                                label="avg wait for a reply"
                                value={
                                    talk.questions.avg_wait_seconds != null
                                        ? `${talk.questions.avg_wait_seconds}s`
                                        : "—"
                                }
                                title="Time from the end of a question to the next utterance"
                            />
                            <Stat
                                label="left hanging"
                                value={talk.questions.hanging}
                                title={`No reply within ${Math.round(talk.questions.hanging_wait_seconds)}s`}
                            />
                        </div>
                        {talk.per_speaker.some((s) => s.questions > 0) && (
                            <div className="mt-2 text-[11px] text-tiilt-muted">
                                {talk.per_speaker
                                    .filter((s) => s.questions > 0)
                                    .map(
                                        (s) =>
                                            `${s.name}: ${s.questions} (${s.open_questions} open)`,
                                    )
                                    .join(" · ")}
                            </div>
                        )}
                    </div>
                </>
            )}

            <div>
                <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Who responds to whom
                </div>
                {data.transitions.length ? (
                    <>
                        <ResponseGraph
                            transitions={data.transitions}
                            colorOf={colorOf}
                            sharesByName={Object.fromEntries(
                                data.speakers.map((s) => [s.name, s.share]),
                            )}
                        />
                        <div className="mt-1 text-[11px] text-tiilt-muted">
                            Arrows point from a speaker to the person they
                            respond to; thicker arrows mean more responses,
                            and larger circles mean more speaking time.
                            {data.transitions.filter((t) => t.from !== t.to).length > 12
                                ? ` Showing the top 12 of ${data.transitions.filter((t) => t.from !== t.to).length} response pairs.`
                                : ""}
                        </div>
                    </>
                 ) : (
                    <div className="text-xs text-tiilt-muted">
                        Not enough turns to build a response network.
                    </div>
                )}
            </div>
        </div>
    )
}
