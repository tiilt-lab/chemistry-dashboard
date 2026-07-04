import { Line } from "react-chartjs-2"
import { Chart as ChartJS } from "chart.js/auto"

// Inline classifier explanations (previously behind a ? dialog).
const FEATURE_DESCRIPTIONS = {
    "Emotional tone":
        "Above 50 is a positive emotional tone; below 50 is negative.",
    "Analytic thinking":
        "Above 50 is analytic thinking; below 50 is narrative thinking.",
    Clout: "Higher scores indicate more confidence or leadership.",
    Authenticity: "Higher scores indicate more honest, authentic communication.",
    Certainty: "Higher scores indicate more certainty or conviction.",
    Confusion: "Higher scores indicate more confusion in a speaker's communication.",
}

const trendClass = (trend) =>
    trend === 1
        ? "text-tiilt-teal"
        : trend === -1
          ? "text-tiilt-danger"
          : "text-tiilt-muted"

const trendGlyph = (trend) => (trend === 1 ? "▲" : trend === -1 ? "▼" : "—")

function FeatureCard({ feature, selectedTime, onSelectTime }) {
    const selectedIndex = feature.time.indexOf(selectedTime)
    const pointRadius = feature.time.map((_, i) =>
        i === selectedIndex ? 5 : 0,
    )
    const pointColor = feature.time.map((_, i) =>
        i === selectedIndex ? "#ec008c" : "#3a2163",
    )
    const selectedValue =
        selectedIndex >= 0 ? Math.round(feature.values[selectedIndex]) : null

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        interaction: { mode: "index", intersect: false },
        onClick: (evt, elements, chart) => {
            if (!onSelectTime) return
            const points = chart.getElementsAtEventForMode(
                evt,
                "index",
                { intersect: false },
                true,
            )
            if (points && points.length) {
                onSelectTime(feature.time[points[0].index])
            }
        },
        scales: {
            x: { display: false },
            y: {
                grid: { color: "rgba(58,33,99,0.08)" },
                ticks: { display: true },
            },
        },
    }

    return (
        <div className="rounded-xl border border-tiilt-line bg-white p-4">
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <div className="text-base font-semibold text-tiilt-ink">
                        {feature.name}
                    </div>
                    {FEATURE_DESCRIPTIONS[feature.name] ? (
                        <div className="mt-0.5 text-sm text-tiilt-muted">
                            {FEATURE_DESCRIPTIONS[feature.name]}
                        </div>
                    ) : (
                        <></>
                    )}
                </div>
                <div className="flex flex-none items-baseline gap-1">
                    {selectedValue !== null ? (
                        <span className="mr-1 rounded-md bg-tiilt-pink/10 px-1.5 py-0.5 text-sm font-semibold text-tiilt-pink tabular-nums">
                            {selectedValue}
                        </span>
                    ) : (
                        <></>
                    )}
                    <span className="text-2xl font-bold text-tiilt-ink tabular-nums">
                        {Math.round(feature.average)}
                    </span>
                    <span className={"text-xs " + trendClass(feature.trend)}>
                        {trendGlyph(feature.trend)}
                    </span>
                </div>
            </div>
            <div className="mt-3 h-28">
                {feature.values.length === 0 ? (
                    <div className="flex h-full items-center justify-center rounded-lg bg-tiilt-ground/60 text-sm text-tiilt-muted">
                        No data for this time range
                    </div>
                ) : (
                    <Line
                        data={{
                            labels: feature.time,
                            datasets: [
                                {
                                    data: feature.values,
                                    borderColor: "#3a2163",
                                    backgroundColor: "rgba(58,33,99,0.08)",
                                    fill: true,
                                    borderWidth: 2,
                                    pointRadius: pointRadius,
                                    pointBackgroundColor: pointColor,
                                    pointBorderColor: pointColor,
                                },
                            ],
                        }}
                        options={options}
                    />
                )}
            </div>
        </div>
    )
}

function FeaturePage(props) {
    const rows = props.showFeatures
        .filter((sf) => sf["clicked"])
        .map((sf) => props.features[sf["value"]])
        .filter((feature) => feature !== undefined)

    return (
        <div className="flex w-full flex-col gap-3">
            {props.features.length > 0 &&
                rows.map((feature, index) => (
                    <FeatureCard
                        key={index}
                        feature={feature}
                        selectedTime={props.selectedTime}
                        onSelectTime={props.onSelectTime}
                    />
                ))}
        </div>
    )
}

export { FeaturePage }
