// Pure formatting for the health panel (Admin > Server health and the
// session's Server load tab), kept apart from React so it is unit-tested.

export function fmtUptime(s) {
    if (s == null || isNaN(s)) return "—"
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return h > 0 ? `${h}h ${m}m` : `${m}m`
}

// "35.0 / 48 GB" from megabytes.
export function fmtGb(usedMb, totalMb) {
    if (usedMb == null || totalMb == null) return "—"
    return `${(usedMb / 1024).toFixed(1)} / ${(totalMb / 1024).toFixed(0)} GB`
}

// Percent of the cores busy on the 1-minute load average, capped so a
// saturated box still draws a full bar instead of overflowing it.
export function cpuPercent(cpu) {
    if (!cpu || cpu.load_1 == null || !cpu.cores) return null
    return Math.min(100, Math.round((100 * cpu.load_1) / cpu.cores))
}

// The one-line verdict above the numbers: the first threshold that trips
// wins, in the order that hurts a live class soonest.
export function healthVerdict(h) {
    if (!h) return null
    const down = Object.entries(h.services || {}).filter(([, s]) => s.active !== "active").map(([n]) => n)
    if (down.length) return { tone: "danger", text: `Service down: ${down.join(", ")}` }
    if (h.gpu && h.gpu.mem_pct >= 92) return { tone: "danger", text: "GPU memory nearly full: the speech recognizer may fail to start for new pods." }
    if (h.disk && h.disk.used_pct >= 92) return { tone: "danger", text: "Disk nearly full: recordings will be refused." }
    if (h.host_ram && h.host_ram.used_pct >= 92) return { tone: "danger", text: "Host RAM nearly full." }
    const cpu = cpuPercent(h.cpu)
    if (cpu != null && cpu >= 100) return { tone: "orange", text: "CPU saturated: live captions may lag." }
    if ((h.gpu && h.gpu.mem_pct >= 80) || (h.host_ram && h.host_ram.used_pct >= 80) || (h.disk && h.disk.used_pct >= 80))
        return { tone: "orange", text: "Resources are getting tight; keep an eye on this page." }
    return { tone: "teal", text: "Server is healthy." }
}
