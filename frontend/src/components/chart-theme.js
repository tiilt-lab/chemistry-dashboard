import { Chart } from "chart.js/auto"
import { isDarkTheme } from "../globals"

// Chart.js can't read CSS variables and resolves its defaults when a chart
// is created, so every chart component calls this in its render body before
// <Line>/<Bar> mounts. Covers tick labels, legends, and grid lines — the
// parts that otherwise stay Chart.js-gray and vanish in dark mode.
export function applyChartTheme() {
    const dark = isDarkTheme()
    Chart.defaults.color = dark ? "#a89fc0" : "#675e7d"
    Chart.defaults.borderColor = dark
        ? "rgba(168, 159, 192, 0.18)"
        : "rgba(103, 94, 125, 0.15)"
}
