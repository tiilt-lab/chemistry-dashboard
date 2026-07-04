import { useState } from "react"
import { Line } from "react-chartjs-2"
import { Chart as ChartJS } from "chart.js/auto"
import { formatSeconds } from "../../globals"

// Per-participant line colors, matching the transcript panel palette.
const SPEAKER_COLORS = [
    "#3a2163",
    "#00a79d",
    "#c0007a",
    "#b26a00",
    "#4d7c1f",
    "#2e3192",
    "#b3261e",
    "#6d28d9",
]

// Recognizable colors per facial-emotion label.
const EMOTION_COLORS = {
    happy: "#4d7c1f",
    serious: "#675e7d",
    neutral: "#a794c9",
    surprise: "#b26a00",
    sad: "#2e3192",
    fear: "#6d28d9",
    disgust: "#b3261e",
    angry: "#b3261e",
}
const EMOTION_FALLBACK = "#a794c9"

// Palette for the top objects of focus; the long tail collapses to "other".
const OBJECT_PALETTE = ["#3a2163", "#00a79d", "#b26a00", "#2e3192", "#8dc63f"]
const OTHER_LABEL = "other"
const OTHER_COLOR = "#c9c2d8"
const ALL = "__all__"
const N_BINS = 72
const TOP_OBJECTS = 5

function inRange(m, start, end) {
    if (start === undefined || end === undefined) return true
    return m.time_stamp >= start && m.time_stamp <= end
}

function tally(values) {
    const counts = {}
    for (const v of values) {
        if (v == null || v === "") continue
        counts[v] = (counts[v] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
}

// Split a participant's samples into N_BINS equal time slots over [t0, t1],
// counting how often each category value appears in each slot.
function binCounts(samples, field, t0, t1, nBins) {
    const span = t1 - t0 || 1
    const bins = Array.from({ length: nBins }, () => ({ counts: {}, total: 0 }))
    for (const s of samples) {
        const v = s[field]
        if (v == null || v === "") continue
        let idx = Math.floor(((s.time_stamp - t0) / span) * nBins)
        if (idx < 0) idx = 0
        if (idx >= nBins) idx = nBins - 1
        bins[idx].counts[v] = (bins[idx].counts[v] || 0) + 1
        bins[idx].total += 1
    }
    return bins
}

function dominant(counts) {
    let best = null
    let bestN = 0
    for (const k in counts) {
        if (counts[k] > bestN) {
            bestN = counts[k]
            best = k
        }
    }
    return best
}

// One participant's state over time: each slot colored by its dominant value.
function Swimlane({ name, bins, colorFor, t0, t1 }) {
    const n = bins.length
    return (
        <div className="flex items-center gap-2">
            <span
                className="w-20 flex-none truncate text-xs text-tiilt-ink"
                title={name}
            >
                {name}
            </span>
            <div className="flex h-4 grow overflow-hidden rounded border border-tiilt-line/60">
                {bins.map((b, i) => {
                    const d = dominant(b.counts)
                    const t = t0 + ((t1 - t0) * (i + 0.5)) / n
                    return (
                        <span
                            key={i}
                            className="h-full flex-1"
                            title={d ? `${formatSeconds(t)} · ${d}` : ""}
                            style={{
                                backgroundColor: d ? colorFor(d) : "transparent",
                            }}
                        />
                    )
                })}
            </div>
        </div>
    )
}

// One category's intensity over time for the selected participant.
function HeatStrip({ label, category, bins, color, t0, t1 }) {
    const n = bins.length
    return (
        <div className="flex items-center gap-2">
            <span
                className="w-20 flex-none truncate text-xs text-tiilt-ink"
                title={label}
            >
                {label}
            </span>
            <div className="flex h-3.5 grow overflow-hidden rounded border border-tiilt-line/60">
                {bins.map((b, i) => {
                    const p = b.total ? (b.counts[category] || 0) / b.total : 0
                    const t = t0 + ((t1 - t0) * (i + 0.5)) / n
                    return (
                        <span
                            key={i}
                            className="h-full flex-1"
                            title={
                                p > 0
                                    ? `${formatSeconds(t)} · ${Math.round(
                                          p * 100,
                                      )}% ${category}`
                                    : ""
                            }
                            style={{
                                backgroundColor: color,
                                opacity: p === 0 ? 0.06 : 0.2 + 0.8 * p,
                            }}
                        />
                    )
                })}
            </div>
        </div>
    )
}

function Axis({ t0, t1 }) {
    return (
        <div className="mt-1 flex gap-2">
            <span className="w-20 flex-none" />
            <div className="font-ahamono flex grow justify-between text-[10px] text-tiilt-muted tabular-nums">
                <span>{formatSeconds(t0)}</span>
                <span>{formatSeconds((t0 + t1) / 2)}</span>
                <span>{formatSeconds(t1)}</span>
            </div>
        </div>
    )
}

// Whole-range mix as a single stacked bar.
function StackedBar({ rows, total, colorFor }) {
    if (total === 0) return null
    return (
        <div className="flex h-2.5 w-full overflow-hidden rounded-full">
            {rows.map(([label, count]) => (
                <span
                    key={label}
                    title={`${label} · ${Math.round((100 * count) / total)}%`}
                    style={{
                        width: (100 * count) / total + "%",
                        backgroundColor: colorFor(label),
                    }}
                />
            ))}
        </div>
    )
}

function Legend({ items, colorFor }) {
    return (
        <div className="flex flex-wrap gap-x-3 gap-y-1">
            {items.map((label) => (
                <span
                    key={label}
                    className="flex items-center gap-1 text-[11px] text-tiilt-muted"
                >
                    <span
                        className="h-2.5 w-2.5 rounded-sm"
                        style={{ backgroundColor: colorFor(label) }}
                    />
                    {label}
                </span>
            ))}
        </div>
    )
}

function SectionHeader({ children }) {
    return (
        <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
            {children}
        </div>
    )
}

function VideoAnalyticsPanel({ videometrics, start, end }) {
    const [selected, setSelected] = useState(ALL)
    const metrics = (videometrics || []).filter((m) => inRange(m, start, end))

    if (metrics.length === 0) {
        return (
            <div className="py-8 text-center text-sm text-tiilt-muted">
                No video analytics in this time range.
            </div>
        )
    }

    // Participants -> stable color.
    const participants = []
    for (const m of metrics) {
        if (m.student_username && !participants.includes(m.student_username)) {
            participants.push(m.student_username)
        }
    }
    const speakerColor = (name) =>
        SPEAKER_COLORS[participants.indexOf(name) % SPEAKER_COLORS.length]

    // Time domain: the extent of the (already range-filtered) video metrics, so
    // the swimlanes and attention chart fill the width and stay aligned. Moving
    // the discussion slider narrows `metrics`, which zooms this domain in.
    const times = metrics.map((m) => m.time_stamp)
    const t0 = Math.min(...times)
    const t1 = Math.max(...times)

    // Object of focus: keep the top N, collapse the rest into "other".
    const topObjects = tally(metrics.map((m) => m.object_on_focus))
        .slice(0, TOP_OBJECTS)
        .map((r) => r[0])
    const topSet = new Set(topObjects)
    const focusOf = (v) => (v ? (topSet.has(v) ? v : OTHER_LABEL) : null)
    const rows = metrics.map((m) => ({ ...m, _focus: focusOf(m.object_on_focus) }))

    const emotionColor = (label) => EMOTION_COLORS[label] || EMOTION_FALLBACK
    const objectColor = (label) =>
        label === OTHER_LABEL
            ? OTHER_COLOR
            : OBJECT_PALETTE[topObjects.indexOf(label) % OBJECT_PALETTE.length]

    // Categories present, most-frequent first.
    const emotionCats = tally(metrics.map((m) => m.facial_emotion)).map(
        (r) => r[0],
    )
    const hasOther = rows.some((r) => r._focus === OTHER_LABEL)
    const objectCats = hasOther ? [...topObjects, OTHER_LABEL] : [...topObjects]

    // Per-participant sample groups.
    const byParticipant = {}
    for (const r of rows) {
        const key = r.student_username || "unknown"
        ;(byParticipant[key] = byParticipant[key] || []).push(r)
    }

    // Attention over time, one line per participant.
    const attnByParticipant = {}
    for (const m of metrics) {
        const key = m.student_username || "unknown"
        ;(attnByParticipant[key] = attnByParticipant[key] || []).push({
            x: m.time_stamp,
            y: m.attention_level,
        })
    }
    const attentionData = {
        datasets: participants.map((name) => ({
            label: name,
            data: attnByParticipant[name].sort((a, b) => a.x - b.x),
            borderColor: speakerColor(name),
            backgroundColor: speakerColor(name),
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
            hidden: selected !== ALL && selected !== name,
        })),
    }
    const attentionOptions = {
        responsive: true,
        maintainAspectRatio: false,
        parsing: false,
        plugins: {
            legend: { display: participants.length > 1, position: "bottom" },
            tooltip: {
                callbacks: {
                    title: (items) =>
                        items.length ? formatSeconds(items[0].parsed.x) : "",
                },
            },
        },
        scales: {
            x: { type: "linear", display: false, min: t0, max: t1 },
            y: {
                grid: { color: "rgba(58,33,99,0.08)" },
                title: { display: true, text: "Attention" },
            },
        },
    }

    const isAll = selected === ALL
    const person = isAll ? null : selected
    const emotionBins = person
        ? binCounts(byParticipant[person] || [], "facial_emotion", t0, t1, N_BINS)
        : null
    const focusBins = person
        ? binCounts(byParticipant[person] || [], "_focus", t0, t1, N_BINS)
        : null

    return (
        <div className="flex w-full flex-col gap-6">
            <div className="flex items-center justify-end">
                <label className="flex items-center gap-2 text-sm text-tiilt-muted">
                    Participant
                    <select
                        value={selected}
                        onChange={(e) => setSelected(e.target.value)}
                        className="cursor-pointer rounded-lg border border-tiilt-line bg-white py-1.5 pr-8 pl-3 text-sm font-semibold text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                    >
                        <option value={ALL}>All participants</option>
                        {participants.map((p) => (
                            <option key={p} value={p}>
                                {p}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            <div>
                <SectionHeader>Attention over time</SectionHeader>
                <div className="h-40">
                    <Line data={attentionData} options={attentionOptions} />
                </div>
            </div>

            <div>
                <SectionHeader>
                    Facial emotion over time
                    {person ? ` · ${person}` : ""}
                </SectionHeader>
                <div className="flex flex-col gap-1.5">
                    {isAll
                        ? participants.map((p) => (
                              <Swimlane
                                  key={p}
                                  name={p}
                                  bins={binCounts(
                                      byParticipant[p] || [],
                                      "facial_emotion",
                                      t0,
                                      t1,
                                      N_BINS,
                                  )}
                                  colorFor={emotionColor}
                                  t0={t0}
                                  t1={t1}
                              />
                          ))
                        : emotionCats.map((c) => (
                              <HeatStrip
                                  key={c}
                                  label={c}
                                  category={c}
                                  bins={emotionBins}
                                  color={emotionColor(c)}
                                  t0={t0}
                                  t1={t1}
                              />
                          ))}
                </div>
                <Axis t0={t0} t1={t1} />
                <div className="mt-2 flex flex-col gap-1.5">
                    <StackedBar
                        rows={tally(
                            (person ? byParticipant[person] : rows).map(
                                (m) => m.facial_emotion,
                            ),
                        )}
                        total={
                            (person ? byParticipant[person] : rows).filter(
                                (m) => m.facial_emotion,
                            ).length
                        }
                        colorFor={emotionColor}
                    />
                    <Legend items={emotionCats} colorFor={emotionColor} />
                </div>
            </div>

            <div>
                <SectionHeader>
                    Object of focus over time
                    {person ? ` · ${person}` : ""}
                </SectionHeader>
                <div className="flex flex-col gap-1.5">
                    {isAll
                        ? participants.map((p) => (
                              <Swimlane
                                  key={p}
                                  name={p}
                                  bins={binCounts(
                                      byParticipant[p] || [],
                                      "_focus",
                                      t0,
                                      t1,
                                      N_BINS,
                                  )}
                                  colorFor={objectColor}
                                  t0={t0}
                                  t1={t1}
                              />
                          ))
                        : objectCats.map((c) => (
                              <HeatStrip
                                  key={c}
                                  label={c}
                                  category={c}
                                  bins={focusBins}
                                  color={objectColor(c)}
                                  t0={t0}
                                  t1={t1}
                              />
                          ))}
                </div>
                <Axis t0={t0} t1={t1} />
                <div className="mt-2 flex flex-col gap-1.5">
                    <StackedBar
                        rows={tally(
                            (person ? byParticipant[person] : rows).map(
                                (m) => m._focus,
                            ),
                        )}
                        total={
                            (person ? byParticipant[person] : rows).filter(
                                (m) => m._focus,
                            ).length
                        }
                        colorFor={objectColor}
                    />
                    <Legend items={objectCats} colorFor={objectColor} />
                </div>
            </div>
        </div>
    )
}

export { VideoAnalyticsPanel }
