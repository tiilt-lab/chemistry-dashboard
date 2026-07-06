import { Line } from "react-chartjs-2"
import { BRAND } from "../../globals"
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

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
        x: { display: false },
        y: { grid: { color: "rgba(58,33,99,0.08)" }, ticks: { display: true } },
    },
}

function FeatureCard({ feature }) {
    return (
        <div
            className="rounded-lg border border-tiilt-line bg-white p-3"
            title={FEATURE_DESCRIPTIONS[feature.name] || ""}
        >
            <div className="flex items-baseline justify-between gap-2">
                <div className="truncate text-sm font-semibold text-tiilt-ink">
                    {feature.name}
                </div>
                <div className="flex flex-none items-baseline gap-1">
                    <span className="text-xl font-bold text-tiilt-ink tabular-nums">
                        {Math.round(feature.average)}
                    </span>
                    <span className={"text-xs " + trendClass(feature.trend)}>
                        {trendGlyph(feature.trend)}
                    </span>
                </div>
            </div>
            <div className="mt-2 h-16">
                {feature.values.length === 0 ? (
                    <div className="flex h-full items-center justify-center rounded-lg bg-tiilt-ground/60 text-xs text-tiilt-muted">
                        No data
                    </div>
                ) : (
                    <Line
                        data={{
                            labels: feature.time,
                            datasets: [
                                {
                                    data: feature.values,
                                    borderColor: BRAND.purple,
                                    backgroundColor: "rgba(58,33,99,0.08)",
                                    fill: true,
                                    borderWidth: 2,
                                    pointRadius: 0,
                                },
                            ],
                        }}
                        options={CHART_OPTIONS}
                    />
                )}
            </div>
        </div>
    )
}

function IndividualFeaturePage(props) {
    const rows = props.showFeatures
        .filter((sf) => sf["clicked"])
        .map((sf) => props.features[sf["value"]])
        .filter((feature) => feature !== undefined)

    return (
        <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            {props.features.length > 0 &&
                rows.map((feature, index) => (
                    <FeatureCard key={index} feature={feature} />
                ))}
        </div>
    )
}

export { IndividualFeaturePage }
