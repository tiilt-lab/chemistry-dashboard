import { useRef, useState, useEffect } from "react"
import { ApiService, withClientKey } from "../../services/api-service"
import { sessionToVideo, videoToSession } from "../video-player/video-time"

// Plays a pod's recorded audio in sync with the transcript, the way
// VideoPlayer does for video pods. /audio/info supplies the duration and the
// segment layout (the recording's clock moves become segments), so the same
// session <-> media mapping in video-time.js serves both players and the
// transcript panel needs no special case.
function AudioPlayer({
    sessionId,
    sessionDeviceId,
    selectedTime,
    onPlaybackTime,
    onSegments,
}) {
    const ref = useRef(null)
    const lastEmit = useRef(0)
    const [status, setStatus] = useState("loading") // loading | ready | missing
    const [segments, setSegments] = useState([])

    // withClientKey appends the pod key for the BYOD join page, whose <audio>
    // element has no login cookie; on logged-in pages it's a no-op.
    const base = withClientKey(
        new ApiService().getEndpoint() +
        `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/audio`)

    useEffect(() => {
        let cancelled = false
        fetch(withClientKey(
            new ApiService().getEndpoint() +
            `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/audio/info`),
            { credentials: "include" })
            .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
            .then((d) => {
                if (cancelled) return
                const segs =
                    Array.isArray(d.segments) && d.segments.length > 0
                        ? d.segments
                        : [{ start: d.offset || 0, video_start: 0, duration: d.duration }]
                setSegments(segs)
                if (onSegments) onSegments(segs)
                setStatus("ready")
            })
            .catch(() => !cancelled && setStatus("missing"))
        return () => {
            cancelled = true
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId, sessionDeviceId])

    // Transcript/graph selection -> seek the audio.
    useEffect(() => {
        const a = ref.current
        if (!a || selectedTime == null || status !== "ready") return
        const target = sessionToVideo(selectedTime, segments)
        if (Math.abs(a.currentTime - target) > 0.75) {
            try {
                a.currentTime = target
            } catch {
                /* metadata not ready yet */
            }
        }
    }, [selectedTime, status, segments])

    const onTimeUpdate = () => {
        const a = ref.current
        if (!a || !onPlaybackTime) return
        const now = a.currentTime
        if (Math.abs(now - lastEmit.current) < 0.5) return
        lastEmit.current = now
        onPlaybackTime(videoToSession(now, segments))
    }

    if (status === "missing") {
        return (
            <div className="rounded-lg border border-dashed border-tiilt-line bg-tiilt-ground py-8 text-center text-sm text-tiilt-muted">
                No recording is available for this pod.
            </div>
        )
    }
    if (status === "loading") {
        return (
            <div className="flex h-16 w-full items-center justify-center rounded-lg bg-tiilt-ground text-sm text-tiilt-muted">
                Preparing audio…
            </div>
        )
    }
    return (
        <div className="flex w-full items-center gap-3 rounded-lg bg-tiilt-ground px-3 py-2">
            <span className="text-xs font-semibold text-tiilt-muted">Audio</span>
            <audio
                ref={ref}
                src={base}
                controls
                preload="metadata"
                onTimeUpdate={onTimeUpdate}
                onSeeked={onTimeUpdate}
                className="w-full"
                aria-label="Pod audio recording"
            />
        </div>
    )
}

export { AudioPlayer }
