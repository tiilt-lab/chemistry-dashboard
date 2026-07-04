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

function inRange(m, start, end) {
    if (start === undefined || end === undefined) return true
    return m.time_stamp >= start && m.time_stamp <= end
}

function Bars({ rows, total, colorFor }) {
    return (
        <div className="flex flex-col gap-1.5">
            {rows.map(([label, count]) => {
                const pct = total > 0 ? Math.round((100 * count) / total) : 0
                return (
                    <div key={label} className="flex items-center gap-2">
                        <span className="w-24 flex-none truncate text-xs text-tiilt-ink">
                            {label}
                        </span>
                        <span className="h-3 grow overflow-hidden rounded-full bg-tiilt-ground">
                            <span
                                className="block h-full rounded-full"
                                style={{
                                    width: pct + "%",
                                    backgroundColor: colorFor(label),
                                }}
                            />
                        </span>
                        <span className="font-ahamono w-9 flex-none text-right text-xs text-tiilt-muted tabular-nums">
                            {pct}%
                        </span>
                    </div>
                )
            })}
        </div>
    )
}

function VideoAnalyticsPanel({ videometrics, start, end }) {
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
    const colorOf = (name) =>
        SPEAKER_COLORS[participants.indexOf(name) % SPEAKER_COLORS.length]

    // Attention over time, one line per participant.
    const byParticipant = {}
    for (const m of metrics) {
        const key = m.student_username || "unknown"
        ;(byParticipant[key] = byParticipant[key] || []).push({
            x: m.time_stamp,
            y: m.attention_level,
        })
    }
    const attentionData = {
        datasets: participants.map((name) => ({
            label: name,
            data: byParticipant[name].sort((a, b) => a.x - b.x),
            borderColor: colorOf(name),
            backgroundColor: colorOf(name),
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2,
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
            x: { type: "linear", display: false },
            y: {
                grid: { color: "rgba(58,33,99,0.08)" },
                title: { display: true, text: "Attention" },
            },
        },
    }

    // Distributions.
    const emotionCounts = tally(metrics.map((m) => m.facial_emotion))
    const objectCounts = tally(metrics.map((m) => m.object_on_focus))
    const topObjects = objectCounts.slice(0, 8)

    return (
        <div className="flex w-full flex-col gap-5">
            <div>
                <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Attention over time
                </div>
                <div className="h-40">
                    <Line data={attentionData} options={attentionOptions} />
                </div>
            </div>

            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <div>
                    <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Facial emotion
                    </div>
                    <Bars
                        rows={emotionCounts}
                        total={metrics.length}
                        colorFor={(label) =>
                            EMOTION_COLORS[label] || "#a794c9"
                        }
                    />
                </div>
                <div>
                    <div className="font-ahamono mb-2 text-[11px] tracking-wider text-tiilt-muted uppercase">
                        Object of focus
                    </div>
                    <Bars
                        rows={topObjects}
                        total={metrics.length}
                        colorFor={() => "#3a2163"}
                    />
                </div>
            </div>
        </div>
    )
}

function tally(values) {
    const counts = {}
    for (const v of values) {
        if (v == null || v === "") continue
        counts[v] = (counts[v] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
}

export { VideoAnalyticsPanel }
