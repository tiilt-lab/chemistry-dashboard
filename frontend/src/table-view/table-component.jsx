import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useOutletContext, useParams } from "react-router-dom"
import { SessionService } from "../services/session-service"
import { Appheader } from "../header/header-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSectionBoxComponent } from "../components/section-box/section-box-component"
import { TranscriptPanel } from "../components/transcript-panel/transcript-panel"
import { VideoPlayer } from "../components/video-player/video-player"
import { AudioPlayer } from "../components/audio-player/audio-player"
import { decorateLines, lineAt, seekFor, toMergedClock } from "./table-time"

// A breakout table: the laptops of one negotiation group as one view. The
// transcript is the merge the coder reads (both laptops, duplicates and
// far-side hearings folded, sentences stitched), each line saying which
// laptop heard it; the media area plays any laptop's video or audio, and
// switching keeps the moment. "Follow the speaker" moves the source to the
// laptop that heard the line now playing, since each side's own laptop
// hears it best.
function SourceButton({ active, disabled, onClick, children, title }) {
    return (
        <button
            type="button"
            disabled={disabled}
            onClick={onClick}
            title={title}
            className={
                "cursor-pointer rounded-md px-2 py-0.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 " +
                (active ? "bg-tiilt text-white" : "bg-white text-tiilt hover:bg-tiilt-soft")
            }
        >
            {children}
        </button>
    )
}

function TableComponent() {
    const [activeSessionService] = useOutletContext()
    const { sessionId, group } = useParams()
    const navigate = useNavigate()
    const [session, setSession] = useState(() => (activeSessionService && activeSessionService.getSession()) || {})
    const [table, setTable] = useState(null) // {group, teams, pods, lines, dropped, alignment}
    const [error, setError] = useState("")
    const [source, setSource] = useState(null) // {deviceId, kind: "video" | "audio"}
    const [videoMissing, setVideoMissing] = useState({})
    const [selectedTime, setSelectedTime] = useState(null) // merged clock
    const [playbackTime, setPlaybackTime] = useState(null) // merged clock
    const [follow, setFollow] = useState(false)
    const lastSwitch = useRef(0)

    useEffect(() => {
        if (Object.keys(session).length <= 0 && activeSessionService) {
            const s = activeSessionService.getSession()
            if (s) setSession(s)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeSessionService])

    useEffect(() => {
        let cancelled = false
        setTable(null)
        setError("")
        new SessionService()
            .getTableTranscript(sessionId, group)
            .then((r) => (r.status === 200 ? r.json() : Promise.reject(r.status)))
            .then((d) => {
                if (cancelled) return
                setTable(d)
                const first = (d.pods || []).find((p) => p.primary) || (d.pods || [])[0]
                if (first) setSource({ deviceId: first.id, kind: "video" })
            })
            .catch((status) => !cancelled && setError(status === 404 ? "This table does not exist." : "The table could not be loaded."))
        return () => {
            cancelled = true
        }
    }, [sessionId, group])

    const lines = useMemo(() => (table ? decorateLines(table.lines, table.pods) : []), [table])
    const alignment = table ? table.alignment : null
    const pods = (table && table.pods) || []
    const sourcePod = pods.find((p) => source && p.id === source.deviceId)

    // The player's seek target, on its laptop's clock.
    const playerSeek = useMemo(() => {
        if (selectedTime == null || !source) return null
        const line = lines.find((l) => l.start_time === selectedTime)
        return line ? seekFor(line, source.deviceId, alignment) : selectedTime
    }, [selectedTime, source, lines, alignment])

    const onPlaybackTime = (deviceSeconds) => {
        if (!source) return
        const merged = toMergedClock(deviceSeconds, source.deviceId, alignment)
        setPlaybackTime(merged)
        if (!follow) return
        const line = lineAt(lines, merged)
        if (!line || line.session_device_id === source.deviceId || !pods.some((p) => p.id === line.session_device_id)) return
        // One switch per few seconds: alternating lines must not thrash the player.
        if (Date.now() - lastSwitch.current < 4000) return
        lastSwitch.current = Date.now()
        switchSource(line.session_device_id, source.kind, merged)
    }

    const switchSource = (deviceId, kind, atMerged) => {
        const at = atMerged != null ? atMerged : playbackTime
        setSource({ deviceId, kind: kind === "video" && videoMissing[deviceId] ? "audio" : kind })
        // Land the new source on the same moment: select the line playing now.
        const line = lineAt(lines, at)
        setSelectedTime(line ? line.start_time : at)
    }

    const title = (session.name || session.title ? (session.name || session.title) + " › " : "") + group
    const back = () => navigate("/sessions/" + sessionId + "/overview")
    const primaries = pods.filter((p) => p.primary)
    const summary = table
        ? `${lines.length} lines merged from ${primaries.map((p) => p.name).join(" and ") || "no laptop"}` +
          (alignment
              ? ` · clocks aligned by ${alignment.method} (${alignment.offset_min} to ${alignment.offset_max} s)`
              : "")
        : ""

    return (
        <div role="main" className="main-container">
            <Appheader title={title} leftText={false} nav={back} escToBack={true} />
            <div className="toolbar-view-container">
                <div className="center-column-container">
                    {error ? (
                        <div className="rounded-lg border border-tiilt-line bg-white p-6 text-sm text-tiilt-muted">{error}</div>
                    ) : !table ? (
                        <div className="flex w-full justify-center py-16">
                            <AppSpinner />
                        </div>
                    ) : (
                        <AppSectionBoxComponent type={"w-full"} heading={"Table video & transcript"}>
                            <div className="flex w-full flex-col gap-3">
                                <div className="flex flex-wrap items-center gap-2 rounded-lg bg-tiilt-ground px-3 py-2">
                                    <span className="text-xs font-semibold text-tiilt-muted">Source</span>
                                    {pods.map((p) => (
                                        <span key={p.id} className="flex items-center gap-1 rounded-md border border-tiilt-line bg-white/60 px-1.5 py-0.5">
                                            <span className="text-xs font-semibold text-tiilt-ink" title={p.primary ? "Carries the merged transcript" : "Media only"}>
                                                {p.side ? `${p.side} · ${p.name}` : p.name}
                                            </span>
                                            {!videoMissing[p.id] ? (
                                                <SourceButton
                                                    active={source && source.deviceId === p.id && source.kind === "video"}
                                                    onClick={() => switchSource(p.id, "video")}
                                                    title="Play this laptop's video"
                                                >
                                                    Video
                                                </SourceButton>
                                            ) : null}
                                            <SourceButton
                                                active={source && source.deviceId === p.id && source.kind === "audio"}
                                                onClick={() => switchSource(p.id, "audio")}
                                                title="Play this laptop's audio recording"
                                            >
                                                Audio
                                            </SourceButton>
                                        </span>
                                    ))}
                                    <label className="ml-auto flex cursor-pointer items-center gap-1 text-xs text-tiilt-muted" title="Play each line from the laptop that heard it">
                                        <input type="checkbox" className="accent-tiilt" checked={follow} onChange={(e) => setFollow(e.target.checked)} />
                                        Follow the speaker
                                    </label>
                                </div>
                                {source && sourcePod ? (
                                    source.kind === "video" && !videoMissing[source.deviceId] ? (
                                        <VideoPlayer
                                            key={"v" + source.deviceId}
                                            sessionId={sessionId}
                                            sessionDeviceId={source.deviceId}
                                            selectedTime={playerSeek}
                                            transcripts={lines.map((l) => ({ ...l, start_time: seekFor(l, source.deviceId, alignment) }))}
                                            onPlaybackTime={onPlaybackTime}
                                            onMissing={() => {
                                                setVideoMissing((m) => ({ ...m, [source.deviceId]: true }))
                                                setSource({ deviceId: source.deviceId, kind: "audio" })
                                            }}
                                        />
                                    ) : (
                                        <AudioPlayer
                                            key={"a" + source.deviceId}
                                            sessionId={sessionId}
                                            sessionDeviceId={source.deviceId}
                                            selectedTime={playerSeek}
                                            onPlaybackTime={onPlaybackTime}
                                        />
                                    )
                                ) : null}
                                <TranscriptPanel
                                    transcripts={lines}
                                    start={0}
                                    end={Number.MAX_SAFE_INTEGER}
                                    selectedTime={selectedTime}
                                    onSelectTime={setSelectedTime}
                                    playbackTime={playbackTime}
                                    transcriptionLabel={summary}
                                />
                            </div>
                        </AppSectionBoxComponent>
                    )}
                </div>
            </div>
        </div>
    )
}

export { TableComponent }
