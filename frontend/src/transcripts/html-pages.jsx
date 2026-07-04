import { GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"

const dlgHeading = "mb-3 text-lg font-semibold text-tiilt-ink"
const dlgBody = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
const dlgClose =
    "mt-2 h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"

function TranscriptComponentPage(props) {
    return (
        <>
            <div className="main-container">
                <Appheader
                    title={"Transcripts · " + props.sessionDevice.name}
                    leftText={false}
                    rightText={"Options"}
                    rightEnabled={props.isenabled}
                    rightTextClick={props.openOptionsDialog}
                    nav={props.navigateToSession}
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
                                            <span className="w-14 font-ahamono text-xs text-tiilt-muted tabular-nums">
                                                {props.formatSeconds(
                                                    transcript.start_time,
                                                )}
                                            </span>
                                        </div>
                                        <div className="min-w-0 grow text-[15px] leading-relaxed text-tiilt-ink">
                                            {transcript.speaker_tag ? (
                                                <span className="font-semibold text-tiilt">
                                                    {transcript.speaker_tag}
                                                    :{" "}
                                                </span>
                                            ) : (
                                                <></>
                                            )}
                                            {transcript.words.map(
                                                (transcriptData, wIndex) =>
                                                    transcriptData.matchingKeywords !==
                                                    null ? (
                                                        <span
                                                            key={wIndex}
                                                            style={{
                                                                color: transcriptData.color,
                                                            }}
                                                            onClick={() =>
                                                                props.openKeywordDialog(
                                                                    transcriptData.matchingKeywords,
                                                                )
                                                            }
                                                            className="cursor-pointer font-semibold underline decoration-dotted underline-offset-2"
                                                        >
                                                            {transcriptData.word +
                                                                " "}
                                                        </span>
                                                    ) : (
                                                        <span key={wIndex}>
                                                            {transcriptData.word +
                                                                " "}
                                                        </span>
                                                    ),
                                            )}
                                        </div>
                                    </li>
                                ),
                            )}
                        </ul>
                    </div>
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
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
                            className={dlgClose}
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
                            className={dlgClose}
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
