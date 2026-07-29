import { useIsDark } from "../../myhooks/custom-hooks"
import { GcaNote } from "./gca-note"
import { applyChartTheme } from "../chart-theme"
import { Line } from "react-chartjs-2"
import { speakerColorFor, formatHMS } from "../../globals"
import "chart.js/auto"

// Group-view counterpart of AppIndividualFeaturesComponent: the same six
// Participation & Impact metrics, but one line per speaker on each card so the
// whole pod can be read at a glance without switching to Individual Comparison.
const METRICS = [
    {
        key: "participation_score",
        name: "Participation",
        description: "How much each speaker participates above or below the group average.",
    },
    {
        key: "social_impact",
        name: "Social Impact",
        description: "How much a speaker's speech is related to the responses that follow it.",
    },
    {
        key: "responsivity",
        name: "Responsivity",
        description: "How much a speaker's responses relate to what others said before.",
    },
    {
        key: "internal_cohesion",
        name: "Internal Cohesion",
        description: "How much a speaker's speech relates to their own earlier speech.",
    },
    {
        key: "newness",
        name: "Newness",
        description: "How much new information a speaker introduces over the session.",
    },
    // communication_density is deliberately absent: the pipeline never computes
    // it (speaker_metrics.py initializes it to zero and posts it unchanged), so
    // the card would always be a flat zero line.
]

// Same smoothing as the individual view, but each speaker's utterances land at
// their own times, so average the chunk's time too instead of assuming a
// shared label axis.
const SMOOTH_WINDOW = 10
function smooth(points) {
    const out = []
    for (let i = 0; i < points.length; i += SMOOTH_WINDOW) {
        const chunk = points.slice(i, i + SMOOTH_WINDOW)
        out.push({
            x: chunk.reduce((sum, p) => sum + p.x, 0) / chunk.length,
            y: chunk.reduce((sum, p) => sum + p.y, 0) / chunk.length,
        })
    }
    return out
}

function buildSeries(transcripts, speakers) {
    return speakers
        .map((speaker) => {
            const perMetric = METRICS.map(() => [])
            for (const t of transcripts || []) {
                // Metric rows only exist for utterances the speaker was
                // matched on — skip the rest.
                const row = (t.speaker_metrics || []).find(
                    (m) => m.speaker_id === speaker.id,
                )
                if (!row) continue
                METRICS.forEach((metric, i) => {
                    const value = row[metric.key]
                    if (typeof value === "number")
                        perMetric[i].push({ x: t.start_time, y: value * 100 })
                })
            }
            return { speaker, perMetric: perMetric.map(smooth) }
        })
        .filter((s) => s.perMetric.some((points) => points.length > 0))
}

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false },
        tooltip: {
            callbacks: {
                title: (items) => formatHMS(items[0].parsed.x),
                label: (ctx) =>
                    `${ctx.dataset.label}: ${Math.round(ctx.parsed.y)}`,
            },
        },
    },
    interaction: { mode: "nearest", intersect: false },
    scales: {
        x: { type: "linear", display: false },
        y: { grid: { color: "rgba(58,33,99,0.08)" }, ticks: { display: true } },
    },
}

function GroupMetricCard({ metric, metricIndex, series, colorOf, dark }) {
    const datasets = series
        .filter((s) => s.perMetric[metricIndex].length > 0)
        .map((s) => ({
            label: s.speaker.alias,
            data: s.perMetric[metricIndex],
            borderColor: colorOf(s.speaker.alias),
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: false,
        }))
    return (
        <div
            className="rounded-lg border border-tiilt-line bg-white p-3"
            title={metric.description}
        >
            <div className="truncate text-sm font-semibold text-tiilt-ink">
                {metric.name}
            </div>
            <div className="mt-2 h-24">
                {datasets.length === 0 ? (
                    <div className="flex h-full items-center justify-center rounded-lg bg-tiilt-ground/60 text-xs text-tiilt-muted">
                        No data
                    </div>
                ) : (
                    <Line
                        key={dark ? "d" : "l"}
                        data={{ datasets }}
                        options={CHART_OPTIONS}
                    />
                )}
            </div>
        </div>
    )
}

function AppGroupFeaturesComponent(props) {
    applyChartTheme()
    const __dark = useIsDark()
    const speakers = props.speakers || []
    const series = buildSeries(props.transcripts, speakers)

    if (series.length === 0)
        return (
            <div className="py-6 text-center text-sm text-tiilt-muted">
                No participation metrics for this pod yet — run Post-Hoc
                Analysis to compute them.
            </div>
        )

    // Palette space is every speaker in the pod (not just those with data), so
    // colors line up with the other panels' canonical speaker colors.
    const allAliases = speakers.map((s) => s.alias)
    const colorOf = (alias) => speakerColorFor(alias, allAliases)

    return (
        <div className="flex w-full flex-col gap-3">
            <GcaNote />
            <div className="flex flex-wrap gap-x-3 gap-y-1">
                {series.map(({ speaker }) => (
                    <span
                        key={speaker.id}
                        className="flex items-center gap-1.5 text-xs text-tiilt-ink"
                    >
                        <span
                            className="h-2.5 w-2.5 flex-none rounded-full"
                            style={{ backgroundColor: colorOf(speaker.alias) }}
                        />
                        {speaker.alias}
                    </span>
                ))}
            </div>
            <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
                {METRICS.map((metric, i) => (
                    <GroupMetricCard
                        key={metric.key}
                        metric={metric}
                        metricIndex={i}
                        series={series}
                        colorOf={colorOf}
                        dark={__dark}
                    />
                ))}
            </div>
        </div>
    )
}

export { AppGroupFeaturesComponent }
