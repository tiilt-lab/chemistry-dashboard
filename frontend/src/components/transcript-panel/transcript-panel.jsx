import { useEffect, useRef } from "react"
import { formatSeconds, speakerColorFor } from "../../globals"

const FEATURE_FIELDS = [
    ["Emotional tone", "emotional_tone_value"],
    ["Analytic thinking", "analytic_thinking_value"],
    ["Clout", "clout_value"],
    ["Authenticity", "authenticity_value"],
    ["Certainty", "certainty_value"],
]

// Distinct, legible-on-white colors assigned per speaker by first appearance.
const SPEAKER_COLORS = [
    "#3a2163",
    "#00a79d",
    "#c0007a",
    "#b26a00",
    "#4d7c1f",
    "#2e3192",
    "#b3261e",
    "#6d28d9",
]

function buildSpeakerColors(transcripts) {
    const tags = [...new Set((transcripts || []).map((t) => t.speaker_tag).filter(Boolean))]
    const map = {}
    for (const tag of tags) map[tag] = speakerColorFor(tag, tags)
    return map
}

// Compact, scrollable transcript list shown inline on the pod-detail page.
// Colors each line by speaker, filters to the selected [start, end] window,
// and links selection with the Expression & Thinking Style graphs.
function TranscriptPanel({
    transcripts,
    start,
    end,
    onOpenFull,
    selectedTime,
    onSelectTime,
    transcriptionLabel,
    playbackTime,
    compact,
}) {
    const scrollRef = useRef(null)
    const selectedRef = useRef(null)
    const playingRef = useRef(null)

    const speakerColors = buildSpeakerColors(transcripts)
    const speakers = Object.keys(speakerColors)

    const list = (transcripts || []).filter((t) => {
        if (start === undefined || end === undefined) return true
        return t.start_time >= start && t.start_time <= end
    })

    // The utterance the video playhead is currently inside (or the most recent
    // one), so the transcript can follow along while the video plays.
    let playingIndex = -1
    if (playbackTime != null) {
        for (let i = 0; i < list.length; i++) {
            if (list[i].start_time <= playbackTime) playingIndex = i
            else break
        }
    }
    const playingKey = playingIndex >= 0 ? list[playingIndex].start_time : null

    // Scroll ONLY the transcript's own container to reveal `el` — never the
    // page. element.scrollIntoView() bubbles to every scrollable ancestor
    // (including the window), which yanks the whole page while the video plays;
    // adjusting container.scrollTop keeps the scroll local (and is a harmless
    // no-op when the transcript isn't its own scroll box).
    const revealInContainer = (el) => {
        const container = scrollRef.current
        if (!el || !container) return
        const er = el.getBoundingClientRect()
        const cr = container.getBoundingClientRect()
        let delta = 0
        if (er.top < cr.top) delta = er.top - cr.top - 8
        else if (er.bottom > cr.bottom) delta = er.bottom - cr.bottom + 8
        if (delta !== 0) {
            container.scrollTo({ top: container.scrollTop + delta, behavior: "smooth" })
        }
    }

    useEffect(() => {
        revealInContainer(selectedRef.current)
    }, [selectedTime])

    // Follow playback: scroll only when the active utterance changes so manual
    // scrolling between utterances isn't constantly fought.
    useEffect(() => {
        revealInContainer(playingRef.current)
    }, [playingKey])

    return (
        <div className="w-full">
            <div className="mb-2 flex flex-col gap-1.5 text-xs text-tiilt-muted sm:flex-row sm:items-center sm:justify-between">
                {(transcripts || []).length > 0 && transcriptionLabel ? (
                    // Provenance describes the stored rows — say nothing when
                    // there are none (or when provenance is unknown).
                    <span>Transcribed with {transcriptionLabel}</span>
                ) : (
                    <span />
                )}
                {speakers.length > 0 ? (
                    <span className="flex flex-wrap gap-x-3 gap-y-1">
                        {speakers.map((tag) => (
                            <span
                                key={tag}
                                className="flex items-center gap-1.5"
                            >
                                <span
                                    className="h-2.5 w-2.5 flex-none rounded-full"
                                    style={{
                                        backgroundColor: speakerColors[tag],
                                    }}
                                />
                                <span className="font-semibold text-tiilt-ink">
                                    {tag}
                                </span>
                            </span>
                        ))}
                    </span>
                ) : (
                    <></>
                )}
            </div>

            {list.length === 0 ? (
                <div className="py-8 text-center text-sm text-tiilt-muted">
                    No transcript in this time range.
                </div>
            ) : (
                <div
                    ref={scrollRef}
                    className={
                        (compact ? "max-h-52" : "max-h-96") +
                        " overflow-y-auto pr-1"
                    }
                >
                    <ul className="flex flex-col gap-0.5">
                        {list.map((t, index) => {
                            const isSelected = t.start_time === selectedTime
                            const isPlaying = index === playingIndex
                            const color = t.speaker_tag
                                ? speakerColors[t.speaker_tag]
                                : "#d5cde4"
                            return (
                                <li
                                    key={index}
                                    ref={
                                        isSelected
                                            ? selectedRef
                                            : isPlaying
                                              ? playingRef
                                              : null
                                    }
                                    onClick={() =>
                                        onSelectTime &&
                                        onSelectTime(
                                            isSelected ? null : t.start_time,
                                        )
                                    }
                                    style={{ borderLeftColor: color }}
                                    className={
                                        "cursor-pointer rounded-r-lg border-l-[3px] py-1 pr-2 pl-3 transition " +
                                        (isSelected
                                            ? "bg-tiilt-soft"
                                            : isPlaying
                                              ? "bg-tiilt-ground ring-1 ring-tiilt-line ring-inset"
                                              : "hover:bg-tiilt-ground/70")
                                    }
                                >
                                    <div className="flex gap-3">
                                        <span className="font-ahamono w-14 flex-none pt-0.5 text-xs text-tiilt-muted tabular-nums">
                                            {formatSeconds(t.start_time)}
                                        </span>
                                        <span className="text-sm leading-snug text-tiilt-ink">
                                            {t.speaker_tag ? (
                                                <span
                                                    className="font-semibold"
                                                    style={{ color }}
                                                >
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
