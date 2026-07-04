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

function FeaturePage(props) {
    const rows = props.showFeatures
        .filter((sf) => sf["clicked"])
        .map((sf) => props.features[sf["value"]])
        .filter((feature) => feature !== undefined)

    return (
        <div className="flex w-full flex-col gap-2">
            {props.features.length > 0 &&
                rows.map((feature, index) => (
                    <div
                        key={index}
                        className="flex items-center gap-4 border-b border-tiilt-line py-3 last:border-b-0"
                    >
                        <div className="min-w-0 grow">
                            <div className="text-sm font-semibold text-tiilt-ink">
                                {feature.name}
                            </div>
                            {FEATURE_DESCRIPTIONS[feature.name] ? (
                                <div className="mt-0.5 text-xs leading-snug text-tiilt-muted">
                                    {FEATURE_DESCRIPTIONS[feature.name]}
                                </div>
                            ) : (
                                <></>
                            )}
                        </div>
                        <div className="flex w-12 flex-none flex-col items-center">
                            <div className="text-xl font-bold text-tiilt-ink tabular-nums">
                                {Math.round(feature.average)}
                            </div>
                            <div
                                className={
                                    "text-[10px] " + trendClass(feature.trend)
                                }
                            >
                                {trendGlyph(feature.trend)}
                            </div>
                        </div>
                        <div className="h-24 w-40 flex-none sm:w-56">
                            {feature.values.length === 0 ? (
                                <div className="flex h-full items-center justify-center text-xs text-tiilt-muted">
                                    No data
                                </div>
                            ) : (
                                <Line
                                    data={{
                                        labels: feature.time,
                                        datasets: [
                                            {
                                                data: feature.values,
                                                borderColor: "#3a2163",
                                                backgroundColor:
                                                    "rgba(58,33,99,0.08)",
                                                fill: true,
                                                borderWidth: 2,
                                                pointRadius: 0,
                                            },
                                        ],
                                    }}
                                    options={{
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        plugins: { legend: { display: false } },
                                        scales: {
                                            x: { display: false },
                                            y: { display: false },
                                        },
                                    }}
                                />
                            )}
                        </div>
                    </div>
                ))}
        </div>
    )
}

export { FeaturePage }
