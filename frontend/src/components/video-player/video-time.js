// Mapping between transcript time (session-relative, from session creation) and
// video time (position in the concatenated recording, disconnect gaps removed).
//
// A pod that dropped and rejoined has several recording segments; the video
// runs them back-to-back, so the mapping is piecewise. segments is
//   [{start, video_start, duration}]  in play order
// where start is the segment's session-relative first frame, video_start is
// where it begins in the concatenated video, and duration is its real length.
// A single-segment pod is one entry, so the same code serves both. Time that
// falls inside a gap (no segment) clamps to the nearest segment edge.

export function sessionToVideo(s, segments) {
    if (!segments || segments.length === 0) return Math.max(s, 0)
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i]
        const dur = seg.duration == null ? Infinity : seg.duration
        if (s < seg.start) return seg.video_start
        if (s < seg.start + dur) return seg.video_start + (s - seg.start)
    }
    const last = segments[segments.length - 1]
    return last.video_start + (last.duration == null ? 0 : last.duration)
}

export function videoToSession(v, segments) {
    if (!segments || segments.length === 0) return Math.max(v, 0)
    for (let i = 0; i < segments.length; i++) {
        const seg = segments[i]
        const dur = seg.duration == null ? Infinity : seg.duration
        if (v < seg.video_start + dur) {
            return seg.start + Math.max(v - seg.video_start, 0)
        }
    }
    const last = segments[segments.length - 1]
    return last.start + (last.duration == null ? 0 : last.duration)
}
