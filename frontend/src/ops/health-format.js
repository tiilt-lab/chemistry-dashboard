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

// Free GPU memory in GB; the recognizer needs ~4 GB per worker and refuses
// to start one below 3.5 GB, so free space is the number that matters, not
// the percentage: the coding model keeps ~26 GB resident all day by design.
export function gpuFreeGb(gpu) {
    if (!gpu || gpu.mem_total_mb == null || gpu.mem_used_mb == null) return null
    return (gpu.mem_total_mb - gpu.mem_used_mb) / 1024
}

// The one-line verdict above the numbers: the first threshold that trips
// wins, in the order that hurts a live class soonest. GPU and disk are
// judged on what is left (a recognizer worker, a class of recordings), RAM
// and CPU on how busy they are.
export function healthVerdict(h) {
    if (!h) return null
    const down = Object.entries(h.services || {}).filter(([, s]) => s.active !== "active").map(([n]) => n)
    if (down.length) return { tone: "danger", text: `Service down: ${down.join(", ")}` }
    const gpuFree = gpuFreeGb(h.gpu)
    if (gpuFree != null && gpuFree < 3.5) return { tone: "danger", text: `GPU memory nearly full (${gpuFree.toFixed(1)} GB free): a speech recognizer worker cannot start.` }
    if (h.disk && h.disk.free_gb != null && h.disk.free_gb < 10) return { tone: "danger", text: `Disk nearly full (${h.disk.free_gb} GB free): recordings will be refused.` }
    if (h.host_ram && h.host_ram.used_pct >= 92) return { tone: "danger", text: "Host RAM nearly full." }
    const cpu = cpuPercent(h.cpu)
    if (cpu != null && cpu >= 100) return { tone: "orange", text: "CPU saturated: live captions may lag." }
    if (gpuFree != null && gpuFree < 6) return { tone: "orange", text: `GPU memory is getting tight (${gpuFree.toFixed(1)} GB free): room for one more recognizer worker at most.` }
    if (h.disk && h.disk.free_gb != null && h.disk.free_gb < 40) return { tone: "orange", text: `Disk is getting full (${h.disk.free_gb} GB free).` }
    if (h.host_ram && h.host_ram.used_pct >= 85) return { tone: "orange", text: "Host RAM is getting tight." }
    return { tone: "teal", text: "Server is healthy." }
}
