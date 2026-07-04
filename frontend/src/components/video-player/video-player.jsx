import { useRef, useState, useEffect, useMemo } from "react"
import { ApiService } from "../../services/api-service"

// Plays a pod's recorded video in sync with the transcript. The server remuxes
// recordings so duration/seeking work; /video/info supplies the real duration
// and the session-relative start offset (video 0:00 = session `offset`s).
//
// Sync model:
//   transcript/graph click (selectedTime, session s) -> seek video to t-offset
//   video playback -> onPlaybackTime(videoTime + offset) so the transcript
//   follows along; subtitles are WebVTT cues built from the transcript.
function formatVttTime(t) {
    const h = String(Math.floor(t / 3600)).padStart(2, "0")
    const m = String(Math.floor((t % 3600) / 60)).padStart(2, "0")
    const s = String(Math.floor(t % 60)).padStart(2, "0")
    const ms = String(Math.round((t % 1) * 1000)).padStart(3, "0")
    return `${h}:${m}:${s}.${ms}`
}

function buildVtt(transcripts, offset) {
    const cues = []
    const list = [...(transcripts || [])].sort(
        (a, b) => a.start_time - b.start_time,
    )
    for (let i = 0; i < list.length; i++) {
        const t = list[i]
        if (!t.transcript) continue
        const start = Math.max(t.start_time - offset, 0)
        // Utterance length when present; otherwise run until the next cue.
        const next = list[i + 1]
        const fallbackEnd = next
            ? Math.max(next.start_time - offset, start + 1)
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
}) {
    const ref = useRef(null)
    const lastEmit = useRef(0)
    const [status, setStatus] = useState("loading") // loading | ready | missing
    const [offset, setOffset] = useState(0)

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
                setOffset(d.offset || 0)
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
        const blob = new Blob([buildVtt(transcripts, offset)], {
            type: "text/vtt",
        })
        return URL.createObjectURL(blob)
    }, [transcripts, offset])
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
        const target = Math.max(selectedTime - offset, 0)
        if (Math.abs(v.currentTime - target) > 0.75) {
            try {
                v.currentTime = target
            } catch {
                /* metadata not ready yet */
            }
        }
    }, [selectedTime, status, offset])

    // Playback -> transcript follow (throttled to ~2 updates/s).
    const onTimeUpdate = () => {
        const v = ref.current
        if (!v || !onPlaybackTime) return
        const now = v.currentTime
        if (Math.abs(now - lastEmit.current) < 0.5) return
        lastEmit.current = now
        onPlaybackTime(now + offset)
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
