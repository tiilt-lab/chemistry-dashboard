import { useEffect, useRef } from "react"
import { GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { SpeakerReassign } from "../components/speaker-reassign"
import { AudioPlayer } from "../components/audio-player/audio-player"
import { lineAt } from "../pod-details/group-time"

import { dlgHeading, dlgBody, dlgCancel } from "../components/dialog-styles"

function TranscriptComponentPage(props) {
    // The line under the playhead: the last one started by then. Revealed
    // inside the list's own scroll box, never by scrolling the page, when
    // it changes (so a reader scrolling elsewhere is not fought every tick).
    const scrollRef = useRef(null)
    const stickyRef = useRef(null)
    const playingRef = useRef(null)
    const playing = props.playbackTime != null ? lineAt(props.displayTranscripts || [], props.playbackTime) : null
    const playingId = playing ? playing.id : null
    useEffect(() => {
        const el = playingRef.current
        const box = scrollRef.current
        if (!el || !box) return
        const er = el.getBoundingClientRect()
        const cr = box.getBoundingClientRect()
        const sticky = stickyRef.current ? stickyRef.current.getBoundingClientRect().height : 0
        const top = cr.top + sticky // under the sticky player
        let delta = 0
        if (er.top < top) delta = er.top - top - 8
        else if (er.bottom > cr.bottom) delta = er.bottom - cr.bottom + 8
        if (delta !== 0) box.scrollTo({ top: box.scrollTop + delta, behavior: "smooth" })
    }, [playingId, props.sessionId])
    const hasPlayer = !!props.sessionId && !!(props.sessionDevice && props.sessionDevice.id)
    const pods = (props.group && props.group.pods) || []
    const playerId = props.groupScope && props.playerDeviceId ? props.playerDeviceId : props.sessionDevice && props.sessionDevice.id
    const groupTitle = props.group && props.sessionDevice && props.sessionDevice.negotiation_group
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Transcripts · " + (props.groupScope && groupTitle ? groupTitle + " · both laptops" : props.sessionDevice.name)}
                    leftText={false}
                    rightText={"Options"}
                    rightTextClick={props.openOptionsDialog}
                    nav={props.navigateToSession}
                    escToBack={true}
                />

                <div ref={scrollRef} className="relative min-h-0 w-full grow overflow-y-auto">
                    {hasPlayer ? (
                        <div ref={stickyRef} className="sticky top-0 z-10 border-b border-tiilt-line bg-white/95 backdrop-blur">
                            <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-4 py-2">
                                {props.group ? (
                                    <div className="flex flex-wrap items-center gap-3 text-xs">
                                        <span className="font-semibold text-tiilt-muted">Transcript</span>
                                        <span className="flex items-center gap-1 rounded-md border border-tiilt-line bg-white p-0.5" title="Whose transcript the page shows">
                                            {[["group", "Whole group"], ["device", "This laptop"]].map(([value, label]) => (
                                                <button
                                                    key={value}
                                                    type="button"
                                                    onClick={() => props.onSelectScope && props.onSelectScope(value)}
                                                    className={
                                                        "cursor-pointer rounded px-2.5 py-1 text-xs font-semibold transition " +
                                                        (props.scope === value ? "bg-tiilt text-white" : "text-tiilt hover:bg-tiilt-soft")
                                                    }
                                                >
                                                    {label}
                                                </button>
                                            ))}
                                        </span>
                                        {props.groupScope ? (
                                            <>
                                                <span className="ml-1 font-semibold text-tiilt-muted">Audio</span>
                                                <span className="flex flex-wrap items-center gap-1">
                                                    {pods.map((p) => {
                                                        const audio = p.has_audio !== false
                                                        const active = playerId === p.id
                                                        return (
                                                            <button
                                                                key={p.id}
                                                                type="button"
                                                                disabled={!audio}
                                                                onClick={() => audio && props.onSelectView && props.onSelectView(p.id)}
                                                                title={audio ? `Play ${p.name}'s recording` : `${p.name} has no recording`}
                                                                className={
                                                                    "rounded-md px-2.5 py-1 text-xs font-semibold transition " +
                                                                    (active
                                                                        ? "bg-tiilt text-white shadow-sm"
                                                                        : audio
                                                                          ? "cursor-pointer bg-tiilt-ground text-tiilt hover:bg-tiilt-soft"
                                                                          : "cursor-default bg-tiilt-ground text-tiilt-muted opacity-60")
                                                                }
                                                            >
                                                                {p.side ? p.side + " · " : ""}{p.name}
                                                            </button>
                                                        )
                                                    })}
                                                </span>
                                            </>
                                        ) : null}
                                    </div>
                                ) : null}
                                <AudioPlayer
                                    key={"a" + playerId}
                                    sessionId={props.sessionId}
                                    sessionDeviceId={playerId}
                                    selectedTime={props.playerSeek != null ? props.playerSeek : props.selectedTime}
                                    onPlaybackTime={props.onPlaybackTime}
                                    onSegments={props.onSegments}
                                />
                            </div>
                        </div>
                    ) : null}
                    <div className="mx-auto w-full max-w-3xl px-4 py-6">
                        {props.chooseClock ? (
                            <div className="mb-3 flex justify-end">
                                <span
                                    className="flex items-center gap-0.5 rounded-md border border-tiilt-line bg-white p-0.5"
                                    title="Elapsed: counted from the first line. Time of day: when the line was spoken, in your time zone."
                                >
                                    {[["elapsed", "Elapsed"], ["wall", "Time of day"]].map(([value, label]) => (
                                        <button
                                            key={value}
                                            type="button"
                                            onClick={() => props.chooseClock(value)}
                                            className={
                                                "rounded px-1.5 py-0.5 text-[11px] font-semibold transition " +
                                                (props.clock === value ? "bg-tiilt text-white" : "text-tiilt hover:bg-tiilt-soft")
                                            }
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </span>
                            </div>
                        ) : null}
                        <ul className="flex flex-col divide-y divide-tiilt-line">
                            {props.displayTranscripts.map(
                                (transcript, index) => (
                                    <li
                                        key={index}
                                        id={`${transcript.id}`}
                                        ref={playingId != null && transcript.id === playingId ? playingRef : null}
                                        className={
                                            "flex gap-4 py-3 transition " +
                                            (transcript.id ===
                                            props.transcriptIndex
                                                ? "rounded-lg bg-tiilt-soft"
                                                : playingId != null && transcript.id === playingId
                                                  ? "rounded-lg bg-tiilt-ground ring-1 ring-tiilt-line ring-inset"
                                                  : "")
                                        }
                                    >
                                        <div className="flex flex-none items-start gap-2 pt-0.5">
                                            <span
                                                className="mt-1 h-4 w-1 flex-none rounded-full"
                                                style={{
                                                    backgroundColor:
                                                        transcript.doaColor ||
                                                        "transparent",
                                                }}
                                                aria-hidden="true"
                                            />
                                            {/* doaColor is color-only; expose the direction to AT too */}
                                            {transcript.direction != null &&
                                            transcript.direction >= 0 ? (
                                                <span className="sr-only">
                                                    {`Speaker direction ${Math.round(transcript.direction)} degrees.`}
                                                </span>
                                            ) : null}
                                            {hasPlayer && props.onSelectTime ? (
                                                <button
                                                    type="button"
                                                    onClick={() => props.onSelectTime(transcript.start_time)}
                                                    title="Play the recording from here"
                                                    className={(props.wallClock ? "w-20" : "w-14") + " font-ahamono cursor-pointer text-left text-xs text-tiilt-muted tabular-nums underline decoration-dotted underline-offset-2 hover:text-tiilt"}
                                                >
                                                    {props.timeLabel
                                                        ? props.timeLabel(transcript.start_time)
                                                        : props.formatSeconds(transcript.start_time)}
                                                </button>
                                            ) : (
                                                <span className={(props.wallClock ? "w-20" : "w-14") + " font-ahamono text-xs text-tiilt-muted tabular-nums"}>
                                                    {props.timeLabel
                                                        ? props.timeLabel(transcript.start_time)
                                                        : props.formatSeconds(transcript.start_time)}
                                                </span>
                                            )}
                                        </div>
                                        <div className="group min-w-0 grow text-[15px] leading-relaxed text-tiilt-ink">
                                            {props.reassignSpeaker ? (
                                                <SpeakerReassign
                                                    tag={transcript.speaker_tag}
                                                    labelOf={props.labelOf}
                                                    color={(props.speakerColors || {})[transcript.speaker_tag]}
                                                    roster={props.roster || []}
                                                    count={
                                                        (props.tagCounts || {})[
                                                            transcript.speaker_tag
                                                        ] || 0
                                                    }
                                                    onReassign={(alias, applyToTag, guest) =>
                                                        props.reassignSpeaker(
                                                            transcript.id,
                                                            alias,
                                                            applyToTag,
                                                            guest,
                                                        )
                                                    }
                                                />
                                            ) : transcript.speaker_tag ? (
                                                <span
                                                    className="font-semibold text-tiilt"
                                                    style={(props.speakerColors || {})[transcript.speaker_tag]
                                                        ? { color: props.speakerColors[transcript.speaker_tag] }
                                                        : undefined}
                                                >
                                                    {props.labelOf ? props.labelOf(transcript.speaker_tag) : transcript.speaker_tag}:{" "}
                                                </span>
                                            ) : (
                                                <></>
                                            )}{" "}
                                            {transcript.speakingOver && transcript.speakingOver.length ? (
                                                <span
                                                    title="Started while the other speaker was still talking"
                                                    className="mr-1 rounded bg-tiilt-soft px-1 align-middle text-[10px] font-semibold text-tiilt"
                                                >
                                                    {"over " +
                                                        transcript.speakingOver
                                                            .map((t) => (props.labelOf ? props.labelOf(t) : t))
                                                            .join(", ")}
                                                </span>
                                            ) : null}
                                            {props.groupScope && transcript.pod_label ? (
                                                <span
                                                    title={transcript.far_side ? "Heard from across the table, named from the partner laptop's roster" : "The laptop that heard this line"}
                                                    className="mr-1 rounded bg-tiilt-ground px-1 align-middle text-[10px] font-medium text-tiilt-muted"
                                                >
                                                    {transcript.pod_label}
                                                </span>
                                            ) : null}
                                            {props.editingId === transcript.id ? (
                                                <textarea
                                                    autoFocus
                                                    value={props.editDraft}
                                                    onChange={(e) =>
                                                        props.setEditDraft(e.target.value)
                                                    }
                                                    onKeyDown={(e) => {
                                                        if (e.key === "Escape") props.cancelEdit()
                                                        if (e.key === "Enter" && !e.shiftKey) {
                                                            e.preventDefault()
                                                            props.saveEdit()
                                                        }
                                                    }}
                                                    onBlur={props.saveEdit}
                                                    rows={Math.max(1, Math.ceil((props.editDraft || "").length / 70))}
                                                    className="w-full rounded-md border border-tiilt bg-white px-1 py-0.5 text-[15px] leading-relaxed text-tiilt-ink outline-none focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                                                />
                                            ) : (
                                                <span
                                                    className="cursor-text"
                                                    title="Click to edit this transcript"
                                                    onClick={() => props.beginEdit && props.beginEdit(transcript)}
                                                >
                                            {transcript.words.map(
                                                (transcriptData, wIndex) =>
                                                    transcriptData.matchingKeywords !==
                                                    null ? (
                                                        <button
                                                            type="button"
                                                            key={wIndex}
                                                            style={{
                                                                color: transcriptData.color,
                                                            }}
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                props.openKeywordDialog(
                                                                    transcriptData.matchingKeywords,
                                                                )
                                                            }}
                                                            aria-label={`Keyword details for ${transcriptData.word}`}
                                                            className="inline cursor-pointer p-0 text-left font-semibold underline decoration-dotted underline-offset-2"
                                                        >
                                                            {transcriptData.word +
                                                                " "}
                                                        </button>
                                                    ) : (
                                                        <span key={wIndex}>
                                                            {transcriptData.word +
                                                                " "}
                                                        </span>
                                                    ),
                                            )}
                                            {props.beginEdit ? (
                                                <button
                                                    type="button"
                                                    onClick={() => props.beginEdit(transcript)}
                                                    title="Edit this transcript text"
                                                    aria-label="Edit transcript text"
                                                    className="ml-1 inline-flex cursor-pointer rounded px-1 text-xs text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                                                >
                                                    ✎
                                                </button>
                                            ) : null}
                                                </span>
                                            )}
                                        </div>
                                    </li>
                                ),
                            )}
                        </ul>
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
                {props.currentForm === "Keyword" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Keyword Data</div>
                        <div className="text-sm text-tiilt-ink">
                            <span className="font-semibold">Word:</span>{" "}
                            {props.dialogKeywords[0].word}
                        </div>
                        <div className="text-sm font-semibold text-tiilt-ink">
                            Keywords (similarity)
                        </div>
                        <div className="flex flex-wrap gap-x-2 gap-y-1 text-sm text-tiilt-muted">
                            {props.dialogKeywords.map((keyword, index) => (
                                <span key={index}>
                                    {keyword.keyword} ({keyword.similarity}%)
                                    {index === props.dialogKeywords.length - 1
                                        ? ""
                                        : ","}
                                </span>
                            ))}
                        </div>
                        <button
                            className={dlgCancel + " mt-2"}
                            onClick={props.closeDialog}
                        >
                            Close
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "Options" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Transcript Options</div>
                        <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-tiilt-ink">
                            <input
                                type="checkbox"
                                checked={props.showKeywords}
                                onChange={props.toggleKeywords}
                                className="h-4 w-4 accent-[var(--color-tiilt)]"
                            />
                            Highlight keywords
                        </label>
                        <div>
                            <div className="mb-1 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                Direction of speech
                            </div>
                            <svg
                                ref={props.legendRef}
                                width={100}
                                height={100 + 10 * 2}
                            ></svg>
                        </div>
                        <button
                            className={dlgCancel + " mt-2"}
                            onClick={props.closeDialog}
                        >
                            Close
                        </button>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>
        </>
    )
}
export { TranscriptComponentPage }
