import { useRef, useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"

// Plays a pod's recorded video beside the transcript, sharing the same
// `selectedTime` used to link the transcript with the Expression & Thinking
// graphs. Clicking a transcript utterance (or a graph point) seeks the video
// here; scrubbing the video highlights the corresponding moment back in the
// transcript. Video time is treated as session-relative seconds, matching the
// transcript start_time domain.
function VideoPlayer({ sessionId, sessionDeviceId, selectedTime, onSelectTime }) {
    const ref = useRef(null)
    const seekingFromProp = useRef(false)
    const [status, setStatus] = useState("loading") // loading | ready | missing

    const src =
        new ApiService().getEndpoint() +
        `api/v1/sessions/${sessionId}/device/${sessionDeviceId}/video`

    // External selection (transcript / graph) -> seek the video.
    useEffect(() => {
        const v = ref.current
        if (!v || selectedTime == null || status !== "ready") return
        if (Math.abs(v.currentTime - selectedTime) > 0.75) {
            seekingFromProp.current = true
            try {
                v.currentTime = selectedTime
            } catch {
                /* metadata not ready yet */
            }
        }
    }, [selectedTime, status])

    // User scrubbed the video -> highlight that moment in the transcript/graphs.
    // Guard against the seeks we triggered ourselves to avoid a feedback loop.
    const onSeeked = () => {
        const v = ref.current
        if (!v) return
        if (seekingFromProp.current) {
            seekingFromProp.current = false
            return
        }
        if (onSelectTime) onSelectTime(Math.floor(v.currentTime))
    }

    if (status === "missing") {
        return (
            <div className="rounded-lg border border-dashed border-tiilt-line bg-tiilt-ground py-8 text-center text-sm text-tiilt-muted">
                No recording is available for this pod.
            </div>
        )
    }

    return (
        <video
            ref={ref}
            src={src}
            controls
            preload="metadata"
            onLoadedMetadata={() => setStatus("ready")}
            onError={() => setStatus("missing")}
            onSeeked={onSeeked}
            className="max-h-[60vh] w-full rounded-lg bg-black"
        />
    )
}

export { VideoPlayer }
