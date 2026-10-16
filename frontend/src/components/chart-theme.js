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
    // Live data: a pod's charts receive the stored history in a couple of
    // bursts and then a row every few seconds. Chart.js animates every
    // update by default (about a second each), which read as the charts
    // flickering; they now redraw in place.
    Chart.defaults.animation = false
}
