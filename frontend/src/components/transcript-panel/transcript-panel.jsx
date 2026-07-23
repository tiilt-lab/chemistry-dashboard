import { useEffect, useRef, useState } from "react"
import { formatSeconds, speakerColorFor } from "../../globals"
import { SpeakerReassign } from "../speaker-reassign"
import { sessionToVideo } from "../video-player/video-time"

const FEATURE_FIELDS = [
    ["Emotional tone", "emotional_tone_value"],
    ["Analytic thinking", "analytic_thinking_value"],
    ["Clout", "clout_value"],
    ["Authenticity", "authenticity_value"],
    ["Certainty", "certainty_value"],
]

// How sure the diarizer was that this line is from the labelled speaker, shown
// inline so a reviewer can spot the shaky attributions to fix first. Amber
// below ~55% (or when two voices overlapped), muted otherwise. Nothing renders
// when there is no score — a clustering-fallback or pre-confidence transcript.
function ConfidenceTag({ percent, contested }) {
    if (percent == null) return null
    const low = contested || percent < 55
    return (
        <span
            title={
                contested
                    ? `Two voices overlapped here (${contested.join(", ")}) — ${percent}% match to the labelled speaker`
                    : `${percent}% match to this speaker's voice print`
            }
            className={
                "font-ahamono text-xs tabular-nums " +
                (low ? "font-semibold text-tiilt-orange-text" : "text-tiilt-muted")
            }
        >
            ({percent}%)
        </span>
    )
}


// RFC-4180 field: quote when it holds a comma, quote, or newline; double any
// internal quotes.
function csvField(value) {
    const s = value == null ? "" : String(value)
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
}

// The visible rows as CSV — the same four columns as the panel (time, speaker,
// confidence, text). Timestamps use whatever clock the panel is showing.
function transcriptsToCsv(rows, displayTime) {
    const header = ["Time", "Speaker", "Confidence", "Transcript"]
    const lines = [header.join(",")]
    for (const t of rows) {
        lines.push(
            [
                formatSeconds(displayTime(t.start_time)),
                t.speaker_tag || "",
                t.speaker_confidence != null ? t.speaker_confidence + "%" : "",
                t.transcript || "",
            ]
                .map(csvField)
                .join(","),
        )
    }
    return lines.join("\n")
}

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
    onEditText,
    onReassignSpeaker,
    roster,
    tagCounts,
    // When present, timestamps are shown on the video's clock (recording-
    // relative) so they match the player, instead of session time. The click
    // target stays in session time — that is what drives the video seek.
    videoSegments,
}) {
    const displayTime = (s) =>
        videoSegments ? sessionToVideo(s, videoSegments) : s

    const downloadCsv = () => {
        const csv = transcriptsToCsv(list, displayTime)
        // BOM so Excel reads UTF-8 (accented names, smart quotes) correctly.
        const blob = new Blob(["﻿" + csv], {
            type: "text/csv;charset=utf-8",
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = "transcript.csv"
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
    }
    const scrollRef = useRef(null)
    const selectedRef = useRef(null)
    const playingRef = useRef(null)

    // Inline text correction (same behavior as the full transcripts page):
    // clicking an utterance opens it for editing in place; Enter or clicking
    // away saves, Esc cancels. The E&T metric chips live on the timestamp.
    const [editingId, setEditingId] = useState(null)
    const [draft, setDraft] = useState("")
    const beginEdit = (t) => {
        if (!onEditText || t.id == null) return
        setEditingId(t.id)
        setDraft(t.transcript || "")
    }
    const commitEdit = async (t) => {
        const clean = (draft || "").trim()
        setEditingId(null)
        if (!clean || clean === t.transcript) return
        await onEditText(t.id, clean)
    }

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
                                        onEditText
                                            ? beginEdit(t)
                                            : onSelectTime &&
                                              onSelectTime(
                                                  isSelected ? null : t.start_time,
                                              )
                                    }
                                    style={{ borderLeftColor: color }}
                                    className={
                                        (onEditText ? "cursor-text" : "cursor-pointer") +
                                        " rounded-r-lg border-l-[3px] py-1 pr-2 pl-3 transition " +
                                        (isSelected
                                            ? "bg-tiilt-soft"
                                            : isPlaying
                                              ? "bg-tiilt-ground ring-1 ring-tiilt-line ring-inset"
                                              : "hover:bg-tiilt-ground/70")
                                    }
                                    title={onEditText ? "Click to edit this transcript" : undefined}
                                >
                                    <div className="flex gap-3">
                                        {/* Column 1 — timestamp */}
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onSelectTime &&
                                                    onSelectTime(
                                                        isSelected ? null : t.start_time,
                                                    )
                                            }}
                                            title={
                                                videoSegments
                                                    ? "Jump the video here"
                                                    : "Show expression & thinking metrics for this utterance"
                                            }
                                            className="font-ahamono w-14 flex-none cursor-pointer pt-0.5 text-left text-xs text-tiilt-muted tabular-nums underline decoration-dotted underline-offset-2 hover:text-tiilt"
                                        >
                                            {formatSeconds(displayTime(t.start_time))}
                                        </button>

                                        {/* Column 2 — speaker (click to reassign) + confidence */}
                                        <div
                                            className="w-28 flex-none overflow-hidden pt-0.5 text-sm leading-snug"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            {onReassignSpeaker && t.id != null ? (
                                                <span className="flex flex-wrap items-center gap-x-1">
                                                    <SpeakerReassign
                                                        tag={t.speaker_tag}
                                                        color={t.speaker_tag ? color : undefined}
                                                        roster={roster || []}
                                                        count={(tagCounts || {})[t.speaker_tag] || 0}
                                                        onReassign={(alias, applyToTag, guest) =>
                                                            onReassignSpeaker(t.id, alias, applyToTag, guest)
                                                        }
                                                    />
                                                    {t.speaker_tag ? (
                                                        <ConfidenceTag
                                                            percent={t.speaker_confidence}
                                                            contested={t.contested}
                                                        />
                                                    ) : null}
                                                </span>
                                            ) : t.speaker_tag ? (
                                                <span className="flex flex-wrap items-center gap-x-1">
                                                    <span
                                                        className="truncate font-semibold"
                                                        style={{ color }}
                                                    >
                                                        {t.speaker_tag}
                                                    </span>
                                                    <ConfidenceTag
                                                        percent={t.speaker_confidence}
                                                        contested={t.contested}
                                                    />
                                                </span>
                                            ) : (
                                                <span className="text-tiilt-muted">—</span>
                                            )}
                                        </div>

                                        {/* Column 3 — transcribed text (or the editor) */}
                                        <div className="min-w-0 flex-1">
                                            {editingId != null && editingId === t.id ? (
                                                <textarea
                                                    autoFocus
                                                    value={draft}
                                                    onChange={(e) => setDraft(e.target.value)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    onKeyDown={(e) => {
                                                        if (e.key === "Escape") setEditingId(null)
                                                        if (e.key === "Enter" && !e.shiftKey) {
                                                            e.preventDefault()
                                                            commitEdit(t)
                                                        }
                                                    }}
                                                    onBlur={() => commitEdit(t)}
                                                    aria-label="Edit transcript text"
                                                    rows={Math.max(1, Math.ceil((draft || "").length / 60))}
                                                    className="w-full rounded-md border border-tiilt bg-white px-1 py-0.5 text-sm leading-snug text-tiilt-ink outline-none focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                                                />
                                            ) : (
                                                <span className="text-sm leading-snug text-tiilt-ink">
                                                    {t.transcript}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    {isSelected ? (
                                        // Indent to align under the text column:
                                        // timestamp 3.5rem + gap + speaker 7rem + gap.
                                        <div className="mt-2 ml-[12rem] flex flex-wrap gap-1.5">
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
            <div className="mt-3 flex items-center justify-between gap-3">
                {onOpenFull ? (
                    <button
                        onClick={onOpenFull}
                        className="text-sm font-semibold text-tiilt hover:underline"
                    >
                        Open full transcript →
                    </button>
                ) : (
                    <span />
                )}
                {list.length > 0 ? (
                    <button
                        onClick={downloadCsv}
                        className="text-sm font-semibold text-tiilt hover:underline"
                    >
                        Download as CSV ↓
                    </button>
                ) : null}
            </div>
        </div>
    )
}

export { TranscriptPanel }
