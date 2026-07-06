import { useIsDark } from "../../myhooks/custom-hooks";
import { applyChartTheme } from "../chart-theme"
import { useState, useRef, useEffect } from "react"
import { Line } from "react-chartjs-2"
import { Chart as ChartJS } from "chart.js/auto"
import { formatSeconds, speakerColorFor } from "../../globals"
import { ModelNote } from "../model-note/model-note"
import { ApiService } from "../../services/api-service"

// Large face card for the participants strip (photo with initials fallback).
function ParticipantCard({ name, color, imgUrl }) {
    const [failed, setFailed] = useState(false)
    return (
        <div className="flex w-20 flex-col items-center gap-1.5">
            <span
                className="relative flex h-16 w-16 flex-none items-center justify-center overflow-hidden rounded-xl text-lg font-bold text-white"
                style={{ backgroundColor: color }}
                aria-hidden="true"
            >
                {initials(name)}
                {imgUrl && !failed ? (
                    <img
                        src={imgUrl}
                        alt={name}
                        onError={() => setFailed(true)}
                        className="absolute inset-0 h-full w-full object-cover"
                    />
                ) : null}
            </span>
            <span
                className="w-full truncate text-center text-xs font-semibold text-tiilt-ink"
                title={name}
            >
                {name}
            </span>
        </div>
    )
}

// Identity avatar: the person's real face crop (saved by the video pipeline)
// overlaid on an initials-in-color chip that shows until/unless the image loads.
function TrackAvatar({ initials, color, imgUrl }) {
    const [failed, setFailed] = useState(false)
    return (
        <span
            className="relative flex h-4 w-4 flex-none items-center justify-center overflow-hidden rounded-full text-[8px] font-bold text-white"
            style={{ backgroundColor: color }}
            aria-hidden="true"
        >
            {initials}
            {imgUrl && !failed ? (
                <img
                    src={imgUrl}
                    alt=""
                    onError={() => setFailed(true)}
                    className="absolute inset-0 h-full w-full object-cover"
                />
            ) : null}
        </span>
    )
}


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
// One category's intensity over time for the selected participant.
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

// Facial-emotion -> valence in [-1, 1], for the fused engagement signal.
const EMOTION_VALENCE = {
    happy: 1,
    happiness: 1,
    surprise: 0.3,
    surprised: 0.3,
    neutral: 0,
    sad: -0.7,
    sadness: -0.7,
    fear: -0.7,
    afraid: -0.7,
    disgust: -0.6,
    anger: -0.8,
    angry: -0.8,
    contempt: -0.5,
}

// Fused engagement per bin from attention + emotional valence, in [0,1].
// engagement = 0.6·(attention/maxAttn) + 0.4·((valence+1)/2).
function engagementCells(samples, t0, t1, nBins, maxAttn) {
    const span = t1 - t0 || 1
    const bins = Array.from({ length: nBins }, () => ({ attn: 0, val: 0, n: 0 }))
    for (const s of samples) {
        let idx = Math.floor(((s.time_stamp - t0) / span) * nBins)
        idx = Math.max(0, Math.min(nBins - 1, idx))
        bins[idx].attn += s.attention_level || 0
        bins[idx].val += EMOTION_VALENCE[(s.facial_emotion || "").toLowerCase()] ?? 0
        bins[idx].n += 1
    }
    const n = bins.length
    return bins.map((b, i) => {
        if (!b.n) return { color: "#16a34a", opacity: 0, title: "" }
        const attnN = maxAttn ? b.attn / b.n / maxAttn : 0
        const valN = (b.val / b.n + 1) / 2
        const e = Math.max(0, Math.min(1, 0.6 * attnN + 0.4 * valN))
        const t = t0 + ((t1 - t0) * (i + 0.5)) / n
        return { color: "#16a34a", opacity: e, title: `${formatSeconds(t)} · ${Math.round(e * 100)}%` }
    })
}

// Rough on-task read from object-of-focus: gaze on a phone reads as off-task,
// no focus reads as disengaged, anything else (people, materials, screen) as
// on-task. Deliberately simple — the object timeline shows the detail.
const OFF_TASK_OBJECTS = new Set(["cell phone", "phone", "cellphone"])
const AWAY_OBJECTS = new Set(["nothing", "none", ""])
function onTaskPct(samples) {
    let on = 0,
        total = 0
    for (const s of samples) {
        const v = (s.object_on_focus || "").toLowerCase()
        total += 1
        if (!OFF_TASK_OBJECTS.has(v) && !AWAY_OBJECTS.has(v)) on += 1
    }
    return total ? Math.round((on / total) * 100) : null
}

// Social attention: fraction of gaze on a person (peers) rather than objects —
// a lightweight #7 signal. Full who-looks-at-whom needs identity threading in
// the video pipeline (target-person identity isn't stored yet).
function socialAttentionPct(samples) {
    let social = 0,
        total = 0
    for (const s of samples) {
        const v = (s.object_on_focus || "").toLowerCase()
        total += 1
        if (v === "person" || v.startsWith("person:")) social += 1
    }
    return total ? Math.round((social / total) * 100) : null
}

// Short initials for an identity avatar chip (usernames are usually one token).
function initials(name) {
    if (!name) return "?"
    const parts = name.replace(/[^a-zA-Z0-9]/g, " ").trim().split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    return name.slice(0, 2).toUpperCase()
}

// Cells for a "dominant value per bin" track (one row per participant).
function swimlaneCells(bins, colorFor, t0, t1) {
    const n = bins.length
    return bins.map((b, i) => {
        const d = dominant(b.counts)
        const t = t0 + ((t1 - t0) * (i + 0.5)) / n
        return {
            color: d ? colorFor(d) : "transparent",
            title: d ? `${formatSeconds(t)} · ${d}` : "",
        }
    })
}

// Cells for a "category intensity per bin" track (one row per category).
function heatCells(bins, category, color, t0, t1) {
    const n = bins.length
    return bins.map((b, i) => {
        const intensity = b.total ? (b.counts[category] || 0) / b.total : 0
        const t = t0 + ((t1 - t0) * (i + 0.5)) / n
        return {
            color,
            opacity: intensity,
            title: `${formatSeconds(t)} · ${Math.round(intensity * 100)}%`,
        }
    })
}

// A stack of aligned category/participant tracks with a fixed label column and
// a shared horizontally-scrollable time area. Draws a playback cursor synced to
// the video (playbackTime, session seconds) and seeks the video on click.
function TimelineTracks({ tracks, t0, t1, zoom, playbackTime, onSeek }) {
    const vpRef = useRef(null)
    const frac =
        playbackTime != null && t1 > t0
            ? Math.min(1, Math.max(0, (playbackTime - t0) / (t1 - t0)))
            : null

    // Keep the cursor in view as the video plays.
    useEffect(() => {
        const vp = vpRef.current
        if (!vp || frac == null) return
        const x = frac * vp.scrollWidth
        if (x < vp.scrollLeft + 24 || x > vp.scrollLeft + vp.clientWidth - 24) {
            vp.scrollLeft = x - vp.clientWidth / 2
        }
    }, [frac, zoom])

    const handleClick = (e) => {
        const vp = vpRef.current
        if (!vp || !onSeek) return
        const rect = vp.getBoundingClientRect()
        const xInContent = e.clientX - rect.left + vp.scrollLeft
        const f = Math.min(1, Math.max(0, xInContent / vp.scrollWidth))
        onSeek(t0 + f * (t1 - t0))
    }

    return (
        <div className="flex gap-2">
            <div className="flex w-24 flex-none flex-col gap-1">
                {tracks.map((tr) => (
                    <div
                        key={tr.name}
                        className="flex h-4 items-center gap-1 text-xs text-tiilt-ink"
                        title={tr.name}
                    >
                        {tr.avatar ? <TrackAvatar {...tr.avatar} /> : null}
                        <span className="truncate">{tr.name}</span>
                    </div>
                ))}
            </div>
            <div
                ref={vpRef}
                onClick={handleClick}
                className="relative grow overflow-x-auto"
                style={{ cursor: onSeek ? "pointer" : "default" }}
            >
                <div
                    className="relative flex flex-col gap-1"
                    style={{ width: `${zoom * 100}%`, minWidth: "100%" }}
                >
                    {tracks.map((tr) => (
                        <div
                            key={tr.name}
                            className="flex h-4 overflow-hidden rounded border border-tiilt-line/60"
                        >
                            {tr.cells.map((c, i) => (
                                <span
                                    key={i}
                                    className="h-full flex-1"
                                    title={c.title}
                                    style={{
                                        backgroundColor: c.color,
                                        opacity: c.opacity == null ? 1 : c.opacity,
                                    }}
                                />
                            ))}
                        </div>
                    ))}
                    {frac != null ? (
                        <div
                            className="pointer-events-none absolute top-0 bottom-0 z-10 w-0.5 bg-tiilt-danger"
                            style={{ left: `${frac * 100}%` }}
                        />
                    ) : null}
                </div>
            </div>
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

function VideoAnalyticsPanel({ videometrics, start, end, models, playbackTime, onSeek, sessionId, sessionDeviceId }) {
    applyChartTheme()
    const __dark = useIsDark()
    const [selected, setSelected] = useState(ALL)
    const [zoom, setZoom] = useState(1)
    const thumbUrl = (alias) =>
        sessionId && sessionDeviceId
            ? new ApiService().getEndpoint() +
              `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/facethumb/${encodeURIComponent(alias)}`
            : null
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
    const speakerColor = (name) => speakerColorFor(name, participants)

    // Time domain: the extent of the (already range-filtered) video metrics, so
    // the swimlanes and attention chart fill the width and stay aligned. Moving
    // the discussion slider narrows `metrics`, which zooms this domain in.
    const times = metrics.map((m) => m.time_stamp)
    const t0 = Math.min(...times)
    const t1 = Math.max(...times)
    const maxAttn = Math.max(1, ...metrics.map((m) => m.attention_level || 0))

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
        onClick: (evt, els, chart) => {
            if (!onSeek || !chart) return
            const val = chart.scales.x.getValueForPixel(evt.x)
            if (val != null && !isNaN(val)) onSeek(val)
        },
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
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-1 text-sm text-tiilt-muted">
                    <span className="mr-1">Zoom</span>
                    <button
                        onClick={() => setZoom((z) => Math.max(1, +(z - 0.5).toFixed(1)))}
                        disabled={zoom <= 1}
                        className="flex h-7 w-7 items-center justify-center rounded-md border border-tiilt-line font-semibold transition hover:bg-tiilt-soft disabled:opacity-40"
                        aria-label="Zoom out"
                    >
                        −
                    </button>
                    <span className="w-8 text-center font-ahamono tabular-nums">
                        {zoom}×
                    </span>
                    <button
                        onClick={() => setZoom((z) => Math.min(8, +(z + 0.5).toFixed(1)))}
                        disabled={zoom >= 8}
                        className="flex h-7 w-7 items-center justify-center rounded-md border border-tiilt-line font-semibold transition hover:bg-tiilt-soft disabled:opacity-40"
                        aria-label="Zoom in"
                    >
                        +
                    </button>
                    {onSeek ? (
                        <span className="ml-2 hidden text-xs text-tiilt-muted sm:inline">
                            · click a timeline to jump the video
                        </span>
                    ) : null}
                </div>
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

            <div className="flex flex-wrap justify-center gap-4">
                {participants.map((p) => (
                    <ParticipantCard
                        key={p}
                        name={p}
                        color={speakerColor(p)}
                        imgUrl={thumbUrl(p)}
                    />
                ))}
            </div>

            <div>
                <SectionHeader>Attention over time</SectionHeader>
                <div className="mb-2">
                    <ModelNote
                        label={models && models.attention && models.attention.label}
                        fallback="Gaze-LLE (DINOv2, open SOTA) + YOLOv5m head detector"
                    />
                </div>
                <div className="h-40">
                    <Line key={__dark ? "d" : "l"}
                        data={attentionData}
                        options={attentionOptions}
                        plugins={[
                            {
                                id: "attnPlaybackCursor",
                                afterDraw(chart) {
                                    if (playbackTime == null) return
                                    const x = chart.scales.x.getPixelForValue(playbackTime)
                                    const area = chart.chartArea
                                    if (x < area.left || x > area.right) return
                                    const ctx = chart.ctx
                                    ctx.save()
                                    ctx.beginPath()
                                    ctx.moveTo(x, area.top)
                                    ctx.lineTo(x, area.bottom)
                                    ctx.lineWidth = 2
                                    ctx.strokeStyle = "#b3261e"
                                    ctx.stroke()
                                    ctx.restore()
                                },
                            },
                        ]}
                    />
                </div>
            </div>

            <div>
                <SectionHeader>
                    Engagement over time
                    {person ? ` · ${person}` : ""}
                </SectionHeader>
                <div className="mb-2 text-xs text-tiilt-muted">
                    Fused from attention + emotional valence — darker = more engaged.
                </div>
                <TimelineTracks
                    tracks={
                        isAll
                            ? participants.map((p) => ({
                                  name: p,
                                  avatar: { initials: initials(p), color: speakerColor(p), imgUrl: thumbUrl(p) },
                                  cells: engagementCells(byParticipant[p] || [], t0, t1, N_BINS, maxAttn),
                              }))
                            : [{
                                  name: person,
                                  cells: engagementCells(byParticipant[person] || [], t0, t1, N_BINS, maxAttn),
                              }]
                    }
                    t0={t0}
                    t1={t1}
                    zoom={zoom}
                    playbackTime={playbackTime}
                    onSeek={onSeek}
                />
                <Axis t0={t0} t1={t1} />
            </div>

            <div>
                <SectionHeader>
                    Facial emotion over time
                    {person ? ` · ${person}` : ""}
                </SectionHeader>
                <div className="mb-2">
                    <ModelNote
                        label={models && models.emotion && models.emotion.label}
                        fallback="HSEmotion EfficientNet-B2 (AffectNet-8)"
                    />
                </div>
                <TimelineTracks
                    tracks={
                        isAll
                            ? participants.map((p) => ({
                                  name: p,
                                  avatar: { initials: initials(p), color: speakerColor(p), imgUrl: thumbUrl(p) },
                                  cells: swimlaneCells(
                                      binCounts(byParticipant[p] || [], "facial_emotion", t0, t1, N_BINS),
                                      emotionColor,
                                      t0,
                                      t1,
                                  ),
                              }))
                            : emotionCats.map((c) => ({
                                  name: c,
                                  cells: heatCells(emotionBins, c, emotionColor(c), t0, t1),
                              }))
                    }
                    t0={t0}
                    t1={t1}
                    zoom={zoom}
                    playbackTime={playbackTime}
                    onSeek={onSeek}
                />
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
                <div className="mb-2">
                    <ModelNote
                        label={models && models.objects && models.objects.label}
                        fallback="YOLO11m object detector (COCO) + gaze direction"
                    />
                </div>
                <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-tiilt-muted">
                    {(isAll ? participants : [person]).map((p) => {
                        const pct = onTaskPct(byParticipant[p] || [])
                        const social = socialAttentionPct(byParticipant[p] || [])
                        return pct == null ? null : (
                            <span key={p}>
                                <span className="font-semibold text-tiilt-ink">
                                    {p}
                                </span>{" "}
                                on-task {pct}%
                                {social != null
                                    ? ` · looking at peers ${social}%`
                                    : ""}
                            </span>
                        )
                    })}
                </div>
                <TimelineTracks
                    tracks={
                        isAll
                            ? participants.map((p) => ({
                                  name: p,
                                  avatar: { initials: initials(p), color: speakerColor(p), imgUrl: thumbUrl(p) },
                                  cells: swimlaneCells(
                                      binCounts(byParticipant[p] || [], "_focus", t0, t1, N_BINS),
                                      objectColor,
                                      t0,
                                      t1,
                                  ),
                              }))
                            : objectCats.map((c) => ({
                                  name: c,
                                  cells: heatCells(focusBins, c, objectColor(c), t0, t1),
                              }))
                    }
                    t0={t0}
                    t1={t1}
                    zoom={zoom}
                    playbackTime={playbackTime}
                    onSeek={onSeek}
                />
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
