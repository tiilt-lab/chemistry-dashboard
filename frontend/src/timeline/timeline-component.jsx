import style from "./timeline.module.css"
import { formatSeconds } from "../globals"

function AppTimeline(props) {
    const sessionLen =
        props.session && props.session.length ? props.session.length : 0
    const transcripts = props.transcripts || []
    const start = props.start !== undefined ? props.start : 0
    const end = props.end !== undefined ? props.end : sessionLen

    // Speech bounds: first utterance start to last utterance end.
    let speechStart = 0
    let speechEnd = sessionLen
    if (transcripts.length) {
        speechStart = Math.min(...transcripts.map((t) => t.start_time))
        speechEnd = Math.max(
            ...transcripts.map((t) => t.start_time + t.length),
        )
    }

    // When no sub-range is selected (the slider spans the whole session),
    // auto-fit the window to the detected speech with a little padding, so the
    // discussion fills the timeline instead of clustering in one corner. A
    // narrower slider selection overrides this and is honored exactly.
    const isFullRange = start <= 0.5 && end >= sessionLen - 0.5
    let winStart = start
    let winEnd = end
    if (isFullRange && transcripts.length && speechEnd > speechStart) {
        const pad = (speechEnd - speechStart) * 0.03
        winStart = Math.max(0, speechStart - pad)
        winEnd = Math.min(sessionLen || speechEnd, speechEnd + pad)
    }
    const duration = Math.max(winEnd - winStart, 0.0001)

    const startText = winStart <= 0 ? "Start" : formatSeconds(winStart)
    const endText =
        winEnd >= sessionLen && sessionLen > 0
            ? props.session && props.session.recording
                ? "Now"
                : "End"
            : formatSeconds(winEnd)

    // Recomputed on every render, so moving the range slider (which changes
    // props.start / props.end) redraws the timeline in step with it.
    const displayTranscripts = transcripts
        .map((transcript) => {
            const left = ((transcript.start_time - winStart) / duration) * 100
            const width = (transcript.length / duration) * 100
            return { transcript, left, width }
        })
        .filter((d) => d.left < 100 && d.left + d.width > 0)
        .map((d) => {
            const left = Math.max(0, d.left)
            return {
                transcript: d.transcript,
                left,
                width: Math.max(0.4, Math.min(d.width, 100 - left)),
            }
        })

    return (
        <div className="w-full">
            <div className={style.legend}>
                <span
                    className={`${style["color-box"]} ${style.question}`}
                ></span>
                <span className={style["legend-text"]}>Question</span>
                <span
                    className={`${style["color-box"]} ${style.discussion}`}
                ></span>
                <span className={style["legend-text"]}>Session</span>
                <span
                    className={`${style["color-box"]} ${style.silence}`}
                ></span>
                <span className={style["legend-text"]}>Silence</span>
            </div>
            <div className={style.line}></div>
            <div className={`${style.timeline} relative`}>
                {displayTranscripts.map((t, index) => (
                    <span
                        key={index}
                        className={
                            t.transcript.question
                                ? `${style["utterance"]} ${style["question"]}`
                                : style["utterance"]
                        }
                        onClick={() => props.clickedTimeline(t.transcript)}
                        style={{ left: `${t.left}%`, width: `${t.width}%` }}
                    ></span>
                ))}
            </div>
            <div className={style["time-textbox"]}>
                <div className={style["time-text"]}>{startText}</div>
                <div className={style["time-text"]}>{endText}</div>
            </div>
        </div>
    )
}

export { AppTimeline }
