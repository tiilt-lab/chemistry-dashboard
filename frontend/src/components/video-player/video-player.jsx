import { useRef, useState, useEffect, useMemo } from "react"
import { ApiService } from "../../services/api-service"
import { sessionToVideo, videoToSession } from "./video-time"

// Plays a pod's recorded video in sync with the transcript. The server remuxes
// recordings so duration/seeking work; /video/info supplies the real duration
// and the segment layout that maps transcript time <-> video time.
//
// A pod that dropped and rejoined has several recording segments, and the
// concatenated video runs them back-to-back with the disconnect gaps removed.
// So the mapping is piecewise, not a single offset: a transcript at session
// time `s` sits in the segment whose [start, start+duration) contains it, and
// its video time is that segment's video_start + (s - start). Time inside a
// gap (no segment) clamps to the nearest segment edge.
//
// segments: [{start, video_start, duration}] in play order. See video-time.js
// for the piecewise session<->video mapping shared with the transcript panel.
function formatVttTime(t) {
    const h = String(Math.floor(t / 3600)).padStart(2, "0")
    const m = String(Math.floor((t % 3600) / 60)).padStart(2, "0")
    const s = String(Math.floor(t % 60)).padStart(2, "0")
    const ms = String(Math.round((t % 1) * 1000)).padStart(3, "0")
    return `${h}:${m}:${s}.${ms}`
}

function buildVtt(transcripts, segments) {
    const cues = []
    const list = [...(transcripts || [])].sort(
        (a, b) => a.start_time - b.start_time,
    )
    for (let i = 0; i < list.length; i++) {
        const t = list[i]
        if (!t.transcript) continue
        const start = sessionToVideo(t.start_time, segments)
        // Utterance length when present; otherwise run until the next cue.
        const next = list[i + 1]
        const fallbackEnd = next
            ? Math.max(sessionToVideo(next.start_time, segments), start + 1)
            : start + 4
        const end = t.length ? start + Math.max(t.length, 1.5) : fallbackEnd
        const speaker = t.speaker_tag ? `<v ${t.speaker_tag}>` : ""
        cues.push(
            `${formatVttTime(start)} --> ${formatVttTime(Math.min(end, fallbackEnd + 30))}\n${speaker}${t.transcript.trim()}`,
        )
    }
    return "WEBVTT\n\n" + cues.join("\n\n")
}

function VideoPlayer({
    sessionId,
    sessionDeviceId,
    selectedTime,
    transcripts,
    onPlaybackTime,
    onSegments,
}) {
    const ref = useRef(null)
    const lastEmit = useRef(0)
    const [status, setStatus] = useState("loading") // loading | ready | missing
    // Segment layout for the transcript<->video mapping. A single-segment pod
    // is one entry synthesised from the scalar offset if the server is older.
    const [segments, setSegments] = useState([])

    const base =
        new ApiService().getEndpoint() +
        `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/video`

    // Real duration + session offset. The first call also triggers the
    // server-side remux, so the <video> that loads after it seeks correctly.
    useEffect(() => {
        let cancelled = false
        fetch(base + "/info", { credentials: "include" })
            .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
            .then((d) => {
                if (cancelled) return
                // Prefer the full segment layout; fall back to a one-segment
                // list built from the scalar offset for older servers.
                const segs =
                    Array.isArray(d.segments) && d.segments.length > 0
                        ? d.segments
                        : [{ start: d.offset || 0, video_start: 0, duration: d.duration || null }]
                setSegments(segs)
                // Share the layout so the transcript panel can label lines on
                // the video's clock instead of session time.
                if (onSegments) onSegments(segs)
                setStatus("ready")
            })
            .catch(() => !cancelled && setStatus("missing"))
        return () => {
            cancelled = true
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId, sessionDeviceId])

    // Subtitles from the transcript, shifted into video time.
    const vttUrl = useMemo(() => {
        if (!transcripts || transcripts.length === 0) return null
        const blob = new Blob([buildVtt(transcripts, segments)], {
            type: "text/vtt",
        })
        return URL.createObjectURL(blob)
    }, [transcripts, segments])
    useEffect(
        () => () => {
            if (vttUrl) URL.revokeObjectURL(vttUrl)
        },
        [vttUrl],
    )

    // Transcript/graph selection -> seek the video.
    useEffect(() => {
        const v = ref.current
        if (!v || selectedTime == null || status !== "ready") return
        const target = sessionToVideo(selectedTime, segments)
        if (Math.abs(v.currentTime - target) > 0.75) {
            try {
                v.currentTime = target
            } catch {
                /* metadata not ready yet */
            }
        }
    }, [selectedTime, status, segments])

    // Playback -> transcript follow (throttled to ~2 updates/s).
    const onTimeUpdate = () => {
        const v = ref.current
        if (!v || !onPlaybackTime) return
        const now = v.currentTime
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
            <div className="flex h-40 w-full items-center justify-center rounded-lg bg-tiilt-ground text-sm text-tiilt-muted">
                Preparing video…
            </div>
        )
    }

    return (
        <video
            ref={ref}
            src={base}
            controls
            preload="metadata"
            crossOrigin="use-credentials"
            onError={() => setStatus("missing")}
            onTimeUpdate={onTimeUpdate}
            className="max-h-[60vh] w-full rounded-lg bg-black"
        >
            {vttUrl ? (
                <track
                    kind="subtitles"
                    label="Transcript"
                    srcLang="en"
                    src={vttUrl}
                    default
                />
            ) : null}
        </video>
    )
}

export { VideoPlayer }
