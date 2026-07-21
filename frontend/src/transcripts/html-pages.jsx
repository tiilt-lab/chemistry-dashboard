import { GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { SpeakerReassign } from "../components/speaker-reassign"

import { dlgHeading, dlgBody, dlgCancel } from "../components/dialog-styles"

function TranscriptComponentPage(props) {
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Transcripts · " + props.sessionDevice.name}
                    leftText={false}
                    rightText={"Options"}
                    rightTextClick={props.openOptionsDialog}
                    nav={props.navigateToSession}
                    escToBack={true}
                />

                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-3xl px-4 py-6">
                        <ul className="flex flex-col divide-y divide-tiilt-line">
                            {props.displayTranscripts.map(
                                (transcript, index) => (
                                    <li
                                        key={index}
                                        id={`${transcript.id}`}
                                        className={
                                            "flex gap-4 py-3 transition " +
                                            (transcript.id ===
                                            props.transcriptIndex
                                                ? "rounded-lg bg-tiilt-soft"
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
                                            <span className="w-14 font-ahamono text-xs text-tiilt-muted tabular-nums">
                                                {props.formatSeconds(
                                                    transcript.start_time,
                                                )}
                                            </span>
                                        </div>
                                        <div className="group min-w-0 grow text-[15px] leading-relaxed text-tiilt-ink">
                                            {props.reassignSpeaker ? (
                                                <SpeakerReassign
                                                    tag={transcript.speaker_tag}
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
                                                    {transcript.speaker_tag}:{" "}
                                                </span>
                                            ) : (
                                                <></>
                                            )}{" "}
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
                {props.currentForm == "Keyword" ? (
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
