import { useRef, useState } from "react"
import { ApiService } from "../../services/api-service"

// Re-runs the recorded audio + video through the post-hoc analysis servers,
// which read the stored recording off disk and regenerate transcripts /
// metrics. Faithful port of the dual-socket protocol:
//   connect -> Initialize_{audio,video}_processing_analytics
//           -> "init posthoc analytics completed"
//           -> start_posthoc_{audio,video}_processing
//           -> "...posthoc analytics started" -> "process_completed"
// with periodic heartbeats while processing.
function PosthocTrigger({ session, sessionDeviceId, speakers }) {
    const api = new ApiService()
    const audioWs = useRef(null)
    const videoWs = useRef(null)
    const heartbeat = useRef(null)
    const [audioState, setAudioState] = useState("idle") // idle|connecting|running|done|error
    const [videoState, setVideoState] = useState("idle")
    const [message, setMessage] = useState("")

    const running = audioState === "connecting" || audioState === "running" ||
        videoState === "connecting" || videoState === "running"

    const speakerList = (speakers || []).map((sp) => ({ id: sp.id, alias: sp.alias }))
    const baseInit = {
        sessionid: session.id,
        server_start: session.creation_date,
        keywords: session.keywords,
        sessiondeviceid: sessionDeviceId,
        speakers: speakerList,
    }

    const startHeartbeat = () => {
        if (heartbeat.current) return
        heartbeat.current = setInterval(() => {
            const hb = JSON.stringify({
                type: "heartbeat_from_posthoc_processing",
                key: "no key (posthoc processing)",
            })
            if (audioWs.current && audioWs.current.readyState === WebSocket.OPEN)
                audioWs.current.send(hb)
            if (videoWs.current && videoWs.current.readyState === WebSocket.OPEN)
                videoWs.current.send(hb)
        }, 20000)
    }

    const maybeStopHeartbeat = (a, v) => {
        const settled = (s) => s === "done" || s === "error" || s === "idle"
        if (settled(a) && settled(v) && heartbeat.current) {
            clearInterval(heartbeat.current)
            heartbeat.current = null
        }
    }

    const openSocket = (endpoint, initType, startType, setState, otherStateRef) => {
        const ws = new WebSocket(endpoint)
        ws.binaryType = "arraybuffer"
        setState("connecting")
        ws.onopen = () => {
            ws.send(JSON.stringify({ ...baseInit, type: initType }))
        }
        ws.onmessage = (e) => {
            if (typeof e.data !== "string") return
            let msg
            try {
                msg = JSON.parse(e.data)
            } catch {
                return
            }
            if (msg.type === "init posthoc analytics completed") {
                ws.send(JSON.stringify({ type: startType }))
                startHeartbeat()
            } else if (
                msg.type === "audio posthoc analytics started" ||
                msg.type === "video posthoc analytics started"
            ) {
                setState("running")
                if (msg.message) setMessage(msg.message)
            } else if (msg.type === "process_completed") {
                setState((prev) => {
                    maybeStopHeartbeat("done", otherStateRef.current)
                    return "done"
                })
            } else if (msg.type === "error") {
                setMessage(msg.message || "Analysis failed.")
                setState("error")
            }
        }
        ws.onclose = () => {
            setState((prev) =>
                prev === "running" || prev === "connecting" ? "error" : prev,
            )
        }
        return ws
    }

    // Keep a ref mirror of each state so a completion handler can check the other.
    const audioRef = useRef("idle")
    const videoRef = useRef("idle")
    const setAudio = (v) => {
        const next = typeof v === "function" ? v(audioRef.current) : v
        audioRef.current = next
        setAudioState(next)
        maybeStopHeartbeat(next, videoRef.current)
    }
    const setVideo = (v) => {
        const next = typeof v === "function" ? v(videoRef.current) : v
        videoRef.current = next
        setVideoState(next)
        maybeStopHeartbeat(audioRef.current, next)
    }

    const run = () => {
        setMessage("")
        audioWs.current = openSocket(
            api.getAudioPosthocWebsocketEndpoint(),
            "Initialize_audio_processing_analytics",
            "start_posthoc_audio_processing",
            setAudio,
            videoRef,
        )
        videoWs.current = openSocket(
            api.getVideoPosthocWebsocketEndpoint(),
            "Initialize_video_processing_analytics",
            "start_posthoc_video_processing",
            setVideo,
            audioRef,
        )
    }

    const label = (s) =>
        s === "idle"
            ? "—"
            : s === "connecting"
              ? "Starting…"
              : s === "running"
                ? "Processing…"
                : s === "done"
                  ? "Complete"
                  : "Failed"

    const color = (s) =>
        s === "done"
            ? "text-tiilt-teal"
            : s === "error"
              ? "text-tiilt-danger"
              : "text-tiilt-muted"

    return (
        <div className="flex w-full flex-col gap-3">
            <div className="text-sm text-tiilt-muted">
                Re-process this pod's recording through the analysis models to
                regenerate its transcript and metrics.
            </div>
            <button
                onClick={run}
                disabled={running}
                className="h-11 w-full max-w-xs rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px disabled:opacity-60 sm:w-auto sm:px-6"
            >
                {running ? "Analysis running…" : "Re-run analysis"}
            </button>
            {audioState !== "idle" || videoState !== "idle" ? (
                <div className="flex flex-col gap-1 text-sm">
                    <div className="flex gap-2">
                        <span className="w-16 text-tiilt-ink">Audio</span>
                        <span className={color(audioState)}>
                            {label(audioState)}
                        </span>
                    </div>
                    <div className="flex gap-2">
                        <span className="w-16 text-tiilt-ink">Video</span>
                        <span className={color(videoState)}>
                            {label(videoState)}
                        </span>
                    </div>
                    {message ? (
                        <div className="mt-1 text-xs text-tiilt-muted">
                            {message}
                        </div>
                    ) : (
                        <></>
                    )}
                    {audioState === "done" && videoState === "done" ? (
                        <div className="mt-1 text-xs text-tiilt-muted">
                            Reload the page to see the regenerated analytics.
                        </div>
                    ) : (
                        <></>
                    )}
                </div>
            ) : (
                <></>
            )}
        </div>
    )
}

export { PosthocTrigger }
