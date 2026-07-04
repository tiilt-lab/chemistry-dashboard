import { useEffect, useRef } from "react"
import { formatSeconds } from "../../globals"

const FEATURE_FIELDS = [
    ["Emotional tone", "emotional_tone_value"],
    ["Analytic thinking", "analytic_thinking_value"],
    ["Clout", "clout_value"],
    ["Authenticity", "authenticity_value"],
    ["Certainty", "certainty_value"],
]

// Compact, scrollable transcript list shown inline on the pod-detail page.
// Filters to the selected [start, end] window so it stays in step with the
// discussion timeline. Clicking an utterance selects it (shared with the
// Expression & Thinking Style graphs via selectedTime); a selection made
// elsewhere scrolls the matching line into view.
function TranscriptPanel({
    transcripts,
    start,
    end,
    onOpenFull,
    selectedTime,
    onSelectTime,
}) {
    const scrollRef = useRef(null)
    const selectedRef = useRef(null)

    const list = (transcripts || []).filter((t) => {
        if (start === undefined || end === undefined) return true
        return t.start_time >= start && t.start_time <= end
    })

    useEffect(() => {
        if (selectedRef.current && scrollRef.current) {
            selectedRef.current.scrollIntoView({
                block: "nearest",
                behavior: "smooth",
            })
        }
    }, [selectedTime])

    return (
        <div className="w-full">
            {list.length === 0 ? (
                <div className="py-8 text-center text-sm text-tiilt-muted">
                    No transcript in this time range.
                </div>
            ) : (
                <div ref={scrollRef} className="max-h-96 overflow-y-auto pr-1">
                    <ul className="flex flex-col divide-y divide-tiilt-line">
                        {list.map((t, index) => {
                            const isSelected = t.start_time === selectedTime
                            return (
                                <li
                                    key={index}
                                    ref={isSelected ? selectedRef : null}
                                    onClick={() =>
                                        onSelectTime &&
                                        onSelectTime(
                                            isSelected ? null : t.start_time,
                                        )
                                    }
                                    className={
                                        "cursor-pointer rounded-lg px-2 py-2 transition " +
                                        (isSelected
                                            ? "bg-tiilt-soft"
                                            : "hover:bg-tiilt-ground/70")
                                    }
                                >
                                    <div className="flex gap-3">
                                        <span className="font-ahamono w-14 flex-none pt-0.5 text-xs text-tiilt-muted tabular-nums">
                                            {formatSeconds(t.start_time)}
                                        </span>
                                        <span className="text-sm leading-relaxed text-tiilt-ink">
                                            {t.speaker_tag ? (
                                                <span className="font-semibold text-tiilt">
                                                    {t.speaker_tag}:{" "}
                                                </span>
                                            ) : (
                                                <></>
                                            )}
                                            {t.transcript}
                                        </span>
                                    </div>
                                    {isSelected ? (
                                        <div className="mt-2 ml-14 flex flex-wrap gap-1.5">
                                            {FEATURE_FIELDS.map(
                                                ([label, field]) => (
                                                    <span
                                                        key={field}
                                                        className="rounded-md bg-white px-2 py-0.5 text-xs text-tiilt-ink ring-1 ring-tiilt-line"
                                                    >
                                                        {label}:{" "}
                                                        <span className="font-semibold tabular-nums">
                                                            {t[field] == null
                                                                ? "—"
                                                                : Math.round(
                                                                      t[field],
                                                                  )}
                                                        </span>
                                                    </span>
                                                ),
                                            )}
                                        </div>
                                    ) : (
                                        <></>
                                    )}
                                </li>
                            )
                        })}
                    </ul>
                </div>
            )}
            {onOpenFull ? (
                <button
                    onClick={onOpenFull}
                    className="mt-3 text-sm font-semibold text-tiilt hover:underline"
                >
                    Open full transcript →
                </button>
            ) : (
                <></>
            )}
        </div>
    )
}

export { TranscriptPanel }
