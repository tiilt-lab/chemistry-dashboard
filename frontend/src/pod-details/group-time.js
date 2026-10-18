// Clocks of a breakout group. The merged transcript sits on the reference
// laptop's session clock; the merge shifted the other laptop's lines by the
// offset it estimated (alignment.offsets: {at, offset} samples on the other
// laptop's clock, merged = device - offset). The players run on their own
// laptop's clock, so a seek or a playback position crosses this mapping
// whenever the source is the other laptop.

function offsetAt(alignment, t) {
    const samples = (alignment && alignment.offsets) || []
    if (!samples.length) return 0
    let best = samples[0]
    for (const s of samples) {
        if (Math.abs(s.at - t) < Math.abs(best.at - t)) best = s
    }
    return best.offset || 0
}

function isOther(alignment, deviceId) {
    return !!alignment && alignment.other_device === deviceId
}

// A merged-clock second as the given laptop's clock second.
export function toDeviceClock(merged, deviceId, alignment) {
    if (merged == null || !isOther(alignment, deviceId)) return merged
    return merged + offsetAt(alignment, merged)
}

// A laptop's clock second as the merged-clock second.
export function toMergedClock(device, deviceId, alignment) {
    if (device == null || !isOther(alignment, deviceId)) return device
    return device - offsetAt(alignment, device)
}

// Where a line plays on a laptop: a line that laptop heard keeps its own
// stamp (device_start_time when the merge moved it); any other line goes
// through the clock mapping.
export function seekFor(line, deviceId, alignment) {
    if (!line) return null
    if (line.session_device_id === deviceId && line.device_start_time != null) return line.device_start_time
    if (line.session_device_id === deviceId) return line.start_time
    return toDeviceClock(line.start_time, deviceId, alignment)
}

// Short label for a laptop in the transcript: its side when the session has
// sides, else its name.
export function podLabel(pod) {
    return (pod && (pod.side || pod.name)) || ""
}

// The merged lines with the panel's extra field: which laptop heard each.
export function decorateLines(lines, pods) {
    const byId = {}
    ;(pods || []).forEach((p) => {
        byId[p.id] = podLabel(p)
    })
    return (lines || []).map((l) => ({ ...l, pod_label: byId[l.session_device_id] || "" }))
}

// The line playing at a merged-clock second: the last one started by then.
export function lineAt(lines, t) {
    if (t == null) return null
    let current = null
    for (const l of lines || []) {
        if (l.start_time <= t) current = l
        else break
    }
    return current
}
