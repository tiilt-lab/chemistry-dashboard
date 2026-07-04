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

// Selectable backends per module. Only transcription and E&T scoring have
// alternative implementations today; the rest are shown (single option,
// locked) so it is explicit what computes each result.
const ASR_OPTIONS = [
    { id: "google-cloud-speech", label: "Google Cloud Speech-to-Text" },
    { id: "whisper", label: "Whisper (open, offline)" },
    { id: "whisperx", label: "WhisperX (open SOTA: batched + word-aligned)" },
    { id: "qwen3", label: "Qwen3-ASR 1.7B (open; leaderboard-best WER, slower)" },
    { id: "qwen3-0.6b", label: "Qwen3-ASR 0.6B (open; fast variant)" },
]
const DIARIZER_OPTIONS = [
    { id: "fingerprint", label: "ECAPA fingerprint matching (enrolled voices)" },
    { id: "pyannote", label: "pyannote 3.1 clustering (open SOTA; WhisperX only)" },
]
const EMBEDDER_OPTIONS = [
    { id: "bge-large-en-v1.5", label: "BGE large v1.5 (open SOTA embedder)" },
    { id: "all-mpnet-base-v2", label: "all-mpnet-base-v2 (matches historical metrics)" },
]
const SCORER_OPTIONS = [
    { id: "liwc", label: "LIWC & Harvard General Inquirer lexicons" },
    { id: "open", label: "Harvard General Inquirer (open)" },
    { id: "llm", label: "Google Gemini (LLM)" },
]

function PosthocTrigger({ session, sessionDeviceId, speakers, transcripts, models }) {
    const api = new ApiService()
    const sockets = useRef([])
    const heartbeat = useRef(null)
    // Per-stream state for the currently running action, keyed by a label
    // ("Audio"/"Video"/"P&I style"/"E&T style"). idle|connecting|running|done|error
    const [streams, setStreams] = useState({})
    const streamsRef = useRef({})
    const [action, setAction] = useState(null) // "full" | "pi" | "et" | null
    const [message, setMessage] = useState("")
    // Model choices for the next run; default to the active deployment config
    // once /api/v1/models arrives.
    const [asrChoice, setAsrChoice] = useState(null)
    const [scorerChoice, setScorerChoice] = useState(null)
    // Post-hoc defaults to the open SOTA stack (batch WhisperX + pyannote),
    // independent of the live pipeline's config default.
    const asr = asrChoice || "whisperx"
    const scorer = scorerChoice || (models && models.scoring && models.scoring.id) || "liwc"
    const [diarizerChoice, setDiarizerChoice] = useState(null)
    const diarizer = diarizerChoice || "pyannote"
    const [embedderChoice, setEmbedderChoice] = useState(null)
    const embedder = embedderChoice || "bge-large-en-v1.5"

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
            // Record which models produced this re-analysis (provenance).
            const modelChoices = {
                asr,
                scorer,
                diarizer,
                embedder,
                emotion: models && models.emotion && models.emotion.id,
                attention: models && models.attention && models.attention.id,
                objects: models && models.objects && models.objects.id,
                keywords: models && models.keywords && models.keywords.id,
            }
            new SessionService()
                .markPosthocCompleted(session.id, sessionDeviceId, modelChoices)
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
                    asr,
                    scorer,
                    diarizer,
                    embedder,
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
                    scorer,
                    embedder,
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

    // Wall-clock estimate for a full re-run, measured on this instance:
    // a 5.5-min recording took ~6.3 min end-to-end (WhisperX transcribes in
    // seconds; the per-utterance semantic/diarization/keyword processing
    // dominates), so estimate ~1.2x the recording length. The pod's recording
    // is often much shorter than the session, so use the transcript extent as
    // the recording-length proxy and fall back to the session length.
    let recordingSeconds = (session && session.length) || 0
    if (transcripts && transcripts.length > 0) {
        const times = transcripts.map((t) => t.start_time)
        recordingSeconds = Math.max(...times) - Math.min(...times) + 30
    }
    // Measured: audio-only ~1.2x recording length; with video ~1.8x (the CV
    // pass runs in parallel but finishes later).
    const estimateFactor = session && session.has_video ? 1.8 : 1.2
    const fullEstimateMin = Math.max(1, Math.ceil((recordingSeconds / 60) * estimateFactor) || 5)

    const btn =
        "h-10 rounded-lg px-4 text-sm font-semibold transition active:translate-y-px disabled:opacity-50"
    const selectCls =
        "w-full cursor-pointer rounded-lg border border-tiilt-line bg-white py-1.5 pr-8 pl-3 text-sm text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 disabled:cursor-default disabled:bg-tiilt-ground disabled:text-tiilt-muted"

    // Config-selected modules: the live label comes from /api/v1/models (the
    // `models` prop); these fallbacks are only shown before that loads, so they
    // track the current default stack rather than the historical one.
    const fixedModules = [
        ["Facial emotion", "emotion", "HSEmotion EfficientNet-B2 (AffectNet-8)"],
        ["Attention / gaze", "attention", "Gaze-LLE (DINOv2) + YOLOv5m heads"],
        ["Object of focus", "objects", "YOLO11m (COCO)"],
        ["Keyword matching", "keywords", "SentenceTransformer (BGE)"],
    ]

    const ModuleRow = ({ name, usedBy, children }) => (
        <div className="grid grid-cols-1 items-center gap-1 sm:grid-cols-[11rem_1fr_10rem] sm:gap-3">
            <span className="text-sm font-semibold text-tiilt-ink">{name}</span>
            {children}
            <span className="text-xs text-tiilt-muted">{usedBy}</span>
        </div>
    )

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

            <div className="flex flex-col gap-2 rounded-lg border border-tiilt-line bg-tiilt-ground/50 p-3">
                <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Models used for the next run
                </div>
                <ModuleRow name="Transcription" usedBy="Full re-run">
                    <select
                        value={asr}
                        onChange={(e) => setAsrChoice(e.target.value)}
                        disabled={running}
                        className={selectCls}
                    >
                        {ASR_OPTIONS.map((o) => (
                            <option key={o.id} value={o.id}>
                                {o.label}
                            </option>
                        ))}
                    </select>
                </ModuleRow>
                <ModuleRow
                    name="P&I semantic cohesion"
                    usedBy="P&I recompute · Full re-run"
                >
                    <select
                        value={embedder}
                        onChange={(e) => setEmbedderChoice(e.target.value)}
                        disabled={running}
                        className={selectCls}
                    >
                        {EMBEDDER_OPTIONS.map((o) => (
                            <option key={o.id} value={o.id}>
                                {o.label}
                            </option>
                        ))}
                    </select>
                </ModuleRow>
                <ModuleRow name="Speaker identification" usedBy="Full re-run">
                    <select
                        value={diarizer}
                        onChange={(e) => setDiarizerChoice(e.target.value)}
                        disabled={running}
                        className={selectCls}
                    >
                        {DIARIZER_OPTIONS.map((o) => (
                            <option key={o.id} value={o.id}>
                                {o.label}
                            </option>
                        ))}
                    </select>
                </ModuleRow>
                <ModuleRow
                    name="E&T scoring"
                    usedBy="Full re-run · E&T recompute"
                >
                    <select
                        value={scorer}
                        onChange={(e) => setScorerChoice(e.target.value)}
                        disabled={running}
                        className={selectCls}
                    >
                        {SCORER_OPTIONS.map((o) => (
                            <option key={o.id} value={o.id}>
                                {o.label}
                            </option>
                        ))}
                    </select>
                </ModuleRow>
                {fixedModules.map(([name, key, fallback]) => (
                    <ModuleRow
                        key={key}
                        name={name}
                        usedBy={
                            key === "participation"
                                ? "P&I recompute · Full re-run"
                                : key === "keywords" || key === "diarization"
                                  ? "Full re-run"
                                  : "Full re-run (video)"
                        }
                    >
                        <select disabled className={selectCls}>
                            <option>
                                {(models && models[key] && models[key].label) ||
                                    fallback}
                            </option>
                        </select>
                    </ModuleRow>
                ))}
                <div className="text-xs text-tiilt-muted">
                    Greyed-out modules have a single implementation; dropdowns
                    apply to the next run you start below.
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                <button
                    onClick={runFull}
                    disabled={running}
                    className={btn + " bg-tiilt text-white hover:bg-tiilt-deep"}
                >
                    Re-run full analysis (~{fullEstimateMin} min)
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
                    Re-compute P&I Style (&lt;1 min)
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
                    Re-compute E&T Style (&lt;1 min)
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
