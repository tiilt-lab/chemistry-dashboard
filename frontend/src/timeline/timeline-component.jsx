import style from "./timeline.module.css"
import { formatSeconds } from "../globals"

function AppTimeline(props) {
    const sessionLen =
        props.session && props.session.length ? props.session.length : 0
    const start = props.start !== undefined ? props.start : 0
    const end = props.end !== undefined ? props.end : sessionLen
    const duration = Math.max(end - start, 0.0001)

    const startText = start === 0 ? "Start" : formatSeconds(start)
    const endText =
        end === sessionLen
            ? props.session && props.session.recording
                ? "Now"
                : "End"
            : formatSeconds(end)

    // Recomputed on every render, so moving the range slider (which changes
    // props.start / props.end) redraws the timeline in step with it.
    const displayTranscripts = (props.transcripts || [])
        .map((transcript) => {
            const left = ((transcript.start_time - start) / duration) * 100
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
                <span className={style["legend-text"]}>Discussion</span>
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
