import { useRef, useState, useEffect, useMemo } from "react"
import { ApiService } from "../../services/api-service"
import { speakerColorFor } from "../../globals"
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

// Overlay toggles for the gaze model's stored geometry. Only shown when the
// pod actually has overlay records (video analyzed after overlay capture).
const OVERLAY_TOGGLES = [
    { key: "heads", label: "Head boxes" },
    { key: "gaze", label: "Gaze rays" },
    { key: "objects", label: "Object of focus" },
    { key: "names", label: "Names" },
]

function VideoPlayer({
    sessionId,
    sessionDeviceId,
    selectedTime,
    transcripts,
    onPlaybackTime,
    onSegments,
}) {
    const ref = useRef(null)
    const canvasRef = useRef(null)
    const lastEmit = useRef(0)
    const [status, setStatus] = useState("loading") // loading | ready | missing
    // Segment layout for the transcript<->video mapping. A single-segment pod
    // is one entry synthesised from the scalar offset if the server is older.
    const [segments, setSegments] = useState([])
    // Gaze overlay records, indexed by whole session-second for fast lookup.
    const [overlays, setOverlays] = useState(null)
    // Toggle choices persist per browser — resetting to all-off on every
    // reload made freshly analyzed overlays look missing.
    const [show, setShow] = useState(() => {
        const defaults = { heads: false, gaze: false, objects: false, names: false }
        try {
            return {
                ...defaults,
                ...JSON.parse(window.localStorage.getItem("gazeOverlayShow") || "{}"),
            }
        } catch (e) {
            return defaults
        }
    })
    const toggleShow = (key) =>
        setShow((s) => {
            const next = { ...s, [key]: !s[key] }
            try {
                window.localStorage.setItem("gazeOverlayShow", JSON.stringify(next))
            } catch (e) {
                // private mode: preference just doesn't persist
            }
            return next
        })

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

    // Gaze overlay geometry (head/gaze/object boxes) stored by the video
    // pipeline. Missing file -> empty records -> no toggle bar renders.
    useEffect(() => {
        let cancelled = false
        new ApiService()
            .httpRequestCall(
                `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/gaze_overlays`,
                "GET",
                {},
            )
            .then((r) => (r.status === 200 ? r.json() : null))
            .then((d) => {
                if (cancelled || !d || !d.records || d.records.length === 0)
                    return
                const bySecond = new Map()
                for (const r of d.records) {
                    const t = Math.round(r.t)
                    if (!bySecond.has(t)) bySecond.set(t, [])
                    bySecond.get(t).push(r)
                }
                setOverlays({
                    bySecond,
                    aliases: [...new Set(d.records.map((r) => r.p))].sort(),
                })
            })
            .catch(() => {})
        return () => {
            cancelled = true
        }
    }, [sessionId, sessionDeviceId])

    // The displayed frame rect inside the <video> element (object-fit:
    // contain letterboxing), so normalized coords land on the real pixels.
    const frameRect = (v) => {
        const vw = v.videoWidth
        const vh = v.videoHeight
        const cw = v.clientWidth
        const ch = v.clientHeight
        if (!vw || !vh || !cw || !ch) return null
        const scale = Math.min(cw / vw, ch / vh)
        const w = vw * scale
        const h = vh * scale
        return { x: (cw - w) / 2, y: (ch - h) / 2, w, h }
    }

    const drawOverlays = () => {
        const v = ref.current
        const canvas = canvasRef.current
        if (!v || !canvas) return
        const dpr = window.devicePixelRatio || 1
        if (canvas.width !== v.clientWidth * dpr) {
            canvas.width = v.clientWidth * dpr
            canvas.height = v.clientHeight * dpr
        }
        const ctx = canvas.getContext("2d")
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        ctx.clearRect(0, 0, v.clientWidth, v.clientHeight)
        if (!overlays || !(show.heads || show.gaze || show.objects || show.names))
            return
        const rect = frameRect(v)
        if (!rect) return
        const sessionSecond = Math.round(videoToSession(v.currentTime, segments))
        // Records land ~1/s; tolerate a 1s gap so playback doesn't flicker.
        const records =
            overlays.bySecond.get(sessionSecond) ||
            overlays.bySecond.get(sessionSecond - 1) ||
            []
        const px = (nx) => rect.x + nx * rect.w
        const py = (ny) => rect.y + ny * rect.h
        for (const r of records) {
            const color = speakerColorFor(r.p, overlays.aliases)
            ctx.lineWidth = 2
            ctx.strokeStyle = color
            ctx.fillStyle = color
            const [hx1, hy1, hx2, hy2] = r.head || []
            if (show.heads && r.head) {
                ctx.strokeRect(px(hx1), py(hy1), px(hx2) - px(hx1), py(hy2) - py(hy1))
            }
            if (show.names && r.head) {
                ctx.font = "600 12px sans-serif"
                const tx = px(hx1)
                const ty = Math.max(12, py(hy1) - 4)
                ctx.save()
                ctx.shadowColor = "rgba(0,0,0,0.8)"
                ctx.shadowBlur = 3
                ctx.fillText(r.p, tx, ty)
                ctx.restore()
            }
            if (show.gaze && r.gaze && r.head) {
                const cx = (px(hx1) + px(hx2)) / 2
                const cy = (py(hy1) + py(hy2)) / 2
                const gx = px(r.gaze[0])
                const gy = py(r.gaze[1])
                ctx.beginPath()
                ctx.moveTo(cx, cy)
                ctx.lineTo(gx, gy)
                ctx.stroke()
                ctx.beginPath()
                ctx.arc(gx, gy, 4, 0, Math.PI * 2)
                ctx.fill()
            }
            if (show.objects && r.obj) {
                const [ox1, oy1, ox2, oy2] = r.obj
                ctx.save()
                ctx.setLineDash([5, 4])
                ctx.strokeRect(px(ox1), py(oy1), px(ox2) - px(ox1), py(oy2) - py(oy1))
                ctx.restore()
                if (r.label) {
                    ctx.font = "11px sans-serif"
                    ctx.save()
                    ctx.shadowColor = "rgba(0,0,0,0.8)"
                    ctx.shadowBlur = 3
                    ctx.fillText(r.label, px(ox1) + 2, py(oy2) - 4)
                    ctx.restore()
                }
            }
        }
    }

    // Repaint when toggles flip or data arrives (also covers paused video).
    useEffect(() => {
        drawOverlays()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [show, overlays, status, segments])

    // The native fullscreen button fullscreens the <video> element ALONE, so
    // the overlay canvas (a sibling) disappears exactly when someone goes
    // fullscreen to watch. Offer container fullscreen instead, which brings
    // the canvas along; repaint on any fullscreen change since the element
    // geometry jumps.
    const containerRef = useRef(null)
    useEffect(() => {
        const onFs = () => setTimeout(drawOverlays, 100)
        document.addEventListener("fullscreenchange", onFs)
        return () => document.removeEventListener("fullscreenchange", onFs)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [overlays, show, segments])
    const toggleContainerFullscreen = () => {
        if (document.fullscreenElement) document.exitFullscreen()
        else if (containerRef.current && containerRef.current.requestFullscreen)
            containerRef.current.requestFullscreen()
    }

    // Playback -> transcript follow (throttled to ~2 updates/s).
    const onTimeUpdate = () => {
        const v = ref.current
        drawOverlays()
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
        <div className="flex w-full flex-col gap-2">
            {overlays && (
                <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-ahamono text-[10px] tracking-wider text-tiilt-muted uppercase">
                        Gaze overlays
                    </span>
                    {OVERLAY_TOGGLES.map((t) => (
                        <button
                            key={t.key}
                            type="button"
                            onClick={() => toggleShow(t.key)}
                            className={
                                "rounded-full border px-2.5 py-0.5 text-xs transition " +
                                (show[t.key]
                                    ? "border-tiilt bg-tiilt-soft font-semibold text-tiilt-ink"
                                    : "border-tiilt-line bg-white text-tiilt-muted hover:bg-tiilt-ground")
                            }
                        >
                            {t.label}
                        </button>
                    ))}
                    <button
                        type="button"
                        onClick={toggleContainerFullscreen}
                        title="Fullscreen with overlays (the video's own fullscreen button hides them)"
                        className="rounded-full border border-tiilt-line bg-white px-2.5 py-0.5 text-xs text-tiilt-muted transition hover:bg-tiilt-ground"
                    >
                        ⛶ fullscreen
                    </button>
                </div>
            )}
            <div
                ref={containerRef}
                className="relative w-full [&:fullscreen]:flex [&:fullscreen]:items-center [&:fullscreen]:justify-center [&:fullscreen]:bg-black [&:fullscreen>video]:h-full [&:fullscreen>video]:max-h-full"
            >
                <video
                    ref={ref}
                    src={base}
                    controls
                    preload="metadata"
                    crossOrigin="use-credentials"
                    onError={() => setStatus("missing")}
                    onTimeUpdate={onTimeUpdate}
                    onSeeked={drawOverlays}
                    onLoadedMetadata={drawOverlays}
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
                <canvas
                    ref={canvasRef}
                    className="pointer-events-none absolute inset-0 h-full w-full"
                />
            </div>
        </div>
    )
}

export { VideoPlayer }
