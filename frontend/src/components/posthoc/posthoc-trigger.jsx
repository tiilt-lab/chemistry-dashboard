import { useRef, useState } from "react"
import { ApiService } from "../../services/api-service"
import { SessionService } from "../../services/session-service"

// Post-hoc re-analysis actions, faithfully ported from the videodev
// pod-component's dual-socket protocol. Three operations:
//
//   full  — re-read the stored recording off disk and regenerate transcript +
//           metrics from scratch (runs ASR). Audio + video sockets, no
//           transcript payload.
//   pi    — re-compute Participation & Impact style from the EXISTING
//           transcript (skips ASR). Audio socket, carries the transcript.
//   et    — re-compute Expressing & Thinking style from the existing
//           transcript. Audio socket, carries the transcript.
//
// Every operation follows: connect -> Initialize_* -> on a readiness ack send
// the matching start_* -> track started -> process_completed, with a 20s
// heartbeat while running.

// Server readiness acks (→ send the operation's start message).
const READY_ACKS = new Set([
    "init posthoc analytics completed",
    "init participation and impact style completed",
    "init expression and thinking style completed",
])
// Server "processing has begun" signals.
const STARTED_ACKS = new Set([
    "audio posthoc analytics started",
    "video posthoc analytics started",
    "speaker metric computation started",
])

function PosthocTrigger({ session, sessionDeviceId, speakers, transcripts }) {
    const api = new ApiService()
    const sockets = useRef([])
    const heartbeat = useRef(null)
    // Per-stream state for the currently running action, keyed by a label
    // ("Audio"/"Video"/"P&I style"/"E&T style"). idle|connecting|running|done|error
    const [streams, setStreams] = useState({})
    const streamsRef = useRef({})
    const [action, setAction] = useState(null) // "full" | "pi" | "et" | null
    const [message, setMessage] = useState("")

    const running = Object.values(streams).some(
        (s) => s === "connecting" || s === "running",
    )

    const speakerList = (speakers || []).map((sp) => ({
        id: sp.id,
        alias: sp.alias,
    }))
    const simplifiedTranscript = (transcripts || []).map((t) => ({
        id: t.id,
        start_time: t.start_time,
        speaker_id: t.speaker_id,
        speaker_tag: t.speaker_tag,
        transcript: t.transcript,
    }))
    const baseInit = {
        sessionid: session.id,
        server_start: session.creation_date,
        keywords: session.keywords,
        sessiondeviceid: sessionDeviceId,
        speakers: speakerList,
    }

    const marked = useRef(false)
    const setStream = (label, value) => {
        streamsRef.current = { ...streamsRef.current, [label]: value }
        setStreams(streamsRef.current)
        const active = Object.values(streamsRef.current)
        const allSettled = active.every(
            (s) => s === "done" || s === "error" || s === "idle",
        )
        if (allSettled && heartbeat.current) {
            clearInterval(heartbeat.current)
            heartbeat.current = null
        }
        // When at least one stream completed successfully, record that this pod
        // has had a post-hoc re-analysis so the sessions list can flag it.
        if (allSettled && !marked.current && active.some((s) => s === "done")) {
            marked.current = true
            new SessionService()
                .markPosthocCompleted(session.id, sessionDeviceId)
                .catch(() => {})
        }
    }

    const startHeartbeat = () => {
        if (heartbeat.current) return
        heartbeat.current = setInterval(() => {
            const hb = JSON.stringify({
                type: "heartbeat_from_posthoc_processing",
                key: "no key (posthoc processing)",
            })
            for (const ws of sockets.current) {
                if (ws && ws.readyState === WebSocket.OPEN) ws.send(hb)
            }
        }, 20000)
    }

    // Open one socket for one operation on one stream.
    const openSocket = ({ endpoint, label, init, startType }) => {
        const ws = new WebSocket(endpoint)
        ws.binaryType = "arraybuffer"
        sockets.current.push(ws)
        setStream(label, "connecting")
        ws.onopen = () => ws.send(JSON.stringify(init))
        ws.onmessage = (e) => {
            if (typeof e.data !== "string") return
            let msg
            try {
                msg = JSON.parse(e.data)
            } catch {
                return
            }
            if (READY_ACKS.has(msg.type)) {
                ws.send(JSON.stringify({ type: startType }))
                startHeartbeat()
            } else if (STARTED_ACKS.has(msg.type)) {
                setStream(label, "running")
                if (msg.message) setMessage(msg.message)
            } else if (msg.type === "process_completed") {
                setStream(label, "done")
            } else if (msg.type === "error") {
                setMessage(msg.message || "Analysis failed.")
                setStream(label, "error")
            }
        }
        ws.onclose = () => {
            const prev = streamsRef.current[label]
            if (prev === "running" || prev === "connecting")
                setStream(label, "error")
        }
    }

    const begin = (kind, defs) => {
        // Reset for a fresh run.
        for (const ws of sockets.current) {
            try {
                ws.close()
            } catch {
                /* noop */
            }
        }
        sockets.current = []
        streamsRef.current = {}
        marked.current = false
        setStreams({})
        setMessage("")
        setAction(kind)
        defs.forEach(openSocket)
    }

    const runFull = () =>
        begin("full", [
            {
                endpoint: api.getAudioPosthocWebsocketEndpoint(),
                label: "Audio",
                startType: "start_posthoc_audio_processing",
                init: {
                    ...baseInit,
                    type: "Initialize_audio_processing_analytics",
                },
            },
            {
                endpoint: api.getVideoPosthocWebsocketEndpoint(),
                label: "Video",
                startType: "start_posthoc_video_processing",
                init: {
                    ...baseInit,
                    type: "Initialize_video_processing_analytics",
                },
            },
        ])

    const runStyle = (kind) => {
        const isPI = kind === "pi"
        begin(kind, [
            {
                endpoint: api.getAudioPosthocWebsocketEndpoint(),
                label: isPI ? "P&I style" : "E&T style",
                startType: isPI
                    ? "start_speaker_transcript_processing"
                    : "start_transcript_metric_processing",
                init: {
                    ...baseInit,
                    type: isPI
                        ? "Initialize_participation_and_impact_style_computation"
                        : "Initialize_expressing_and_thinking_style_computation",
                    transcript: simplifiedTranscript,
                },
            },
        ])
    }

    const hasTranscript = simplifiedTranscript.length > 0

    const label = (s) =>
        s === "connecting"
            ? "Starting…"
            : s === "running"
              ? "Processing…"
              : s === "done"
                ? "Complete"
                : s === "error"
                  ? "Failed"
                  : "—"
    const color = (s) =>
        s === "done"
            ? "text-tiilt-teal"
            : s === "error"
              ? "text-tiilt-danger"
              : "text-tiilt-muted"

    const btn =
        "h-10 rounded-lg px-4 text-sm font-semibold transition active:translate-y-px disabled:opacity-50"

    return (
        <div className="flex w-full flex-col gap-4">
            <div>
                <div className="text-sm text-tiilt-muted">
                    Re-process this pod through the analysis models. A full
                    re-run reads the stored recording off disk and regenerates
                    the transcript and all metrics; the style re-computations
                    re-score the existing transcript only (no re-transcription).
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                <button
                    onClick={runFull}
                    disabled={running}
                    className={btn + " bg-tiilt text-white hover:bg-tiilt-deep"}
                >
                    Re-run full analysis
                </button>
                <button
                    onClick={() => runStyle("pi")}
                    disabled={running || !hasTranscript}
                    title={
                        hasTranscript
                            ? ""
                            : "No transcript available to re-score."
                    }
                    className={
                        btn +
                        " border border-tiilt-line bg-white text-tiilt-ink hover:border-tiilt hover:bg-tiilt-soft"
                    }
                >
                    Re-compute P&I Style
                </button>
                <button
                    onClick={() => runStyle("et")}
                    disabled={running || !hasTranscript}
                    title={
                        hasTranscript
                            ? ""
                            : "No transcript available to re-score."
                    }
                    className={
                        btn +
                        " border border-tiilt-line bg-white text-tiilt-ink hover:border-tiilt hover:bg-tiilt-soft"
                    }
                >
                    Re-compute E&T Style
                </button>
            </div>

            {action && Object.keys(streams).length > 0 ? (
                <div className="flex flex-col gap-1 text-sm">
                    {Object.entries(streams).map(([name, state]) => (
                        <div key={name} className="flex gap-2">
                            <span className="w-20 text-tiilt-ink">{name}</span>
                            <span className={color(state)}>{label(state)}</span>
                        </div>
                    ))}
                    {message ? (
                        <div className="mt-1 text-xs text-tiilt-muted">
                            {message}
                        </div>
                    ) : (
                        <></>
                    )}
                    {Object.values(streams).length > 0 &&
                    Object.values(streams).every((s) => s === "done") ? (
                        <div className="mt-1 text-xs text-tiilt-muted">
                            Reload the page to see the updated analytics.
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
