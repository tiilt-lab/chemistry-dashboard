import { formatSeconds } from "../../globals"

// Compact, scrollable transcript list shown inline on the pod-detail page.
// Filters to the selected [start, end] window so it stays in step with the
// discussion timeline and range slider.
function TranscriptPanel({ transcripts, start, end, onOpenFull }) {
    const list = (transcripts || []).filter((t) => {
        if (start === undefined || end === undefined) return true
        return t.start_time >= start && t.start_time <= end
    })

    return (
        <div className="w-full">
            {list.length === 0 ? (
                <div className="py-8 text-center text-sm text-tiilt-muted">
                    No transcript in this time range.
                </div>
            ) : (
                <div className="max-h-96 overflow-y-auto pr-1">
                    <ul className="flex flex-col divide-y divide-tiilt-line">
                        {list.map((t, index) => (
                            <li key={index} className="flex gap-3 py-2">
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
                            </li>
                        ))}
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
