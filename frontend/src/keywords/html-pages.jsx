import React from "react"
import { DialogBox } from "../dialog/dialog-component"

const MAX_INLINE = 25

// One chip per detected keyword: a similarity-tinted dot, the word, and how
// often it came up. Clicking opens the strongest matching utterance in the
// transcript.
function KeywordChip({ k, onClick }) {
    return (
        <button
            type="button"
            onClick={onClick}
            title={`Strongest match ${Math.round(k.similarity)}% · said ${k.count} ${k.count === 1 ? "time" : "times"} — open in transcript`}
            className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-tiilt-line bg-white px-2.5 py-1 text-xs font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft"
        >
            <span
                className="h-2 w-2 flex-none rounded-full"
                style={{ backgroundColor: k.color }}
                aria-hidden="true"
            />
            {k.word}
            {k.count > 1 ? (
                <span className="font-ahamono text-[10px] font-normal text-tiilt-muted">
                    ×{k.count}
                </span>
            ) : null}
        </button>
    )
}

function segButton(active) {
    return (
        "cursor-pointer rounded-full px-3 py-1 text-xs font-semibold transition " +
        (active
            ? "bg-tiilt text-white"
            : "bg-tiilt-line/40 text-tiilt-muted hover:bg-tiilt-soft hover:text-tiilt")
    )
}

function AppKeywordsPage(props) {
    const configured = (props.session.keywords || []).length > 0
    const inline = props.displayKeywords.slice(0, MAX_INLINE)
    const overflow = props.displayKeywords.length - inline.length

    return (
        <>
            <div className="w-full">
                <div className="mb-3 flex items-center justify-between gap-3">
                    <div className="text-[11px] text-tiilt-muted">
                        {props.displayKeywords.length > 0
                            ? "Deeper dot = stronger match · click a keyword to open it in the transcript"
                            : null}
                    </div>
                    <div className="flex flex-none gap-1" role="tablist" aria-label="Keyword view">
                        <button
                            role="tab"
                            aria-selected={!props.showGraph}
                            className={segButton(!props.showGraph)}
                            onClick={() => props.setShowGraph(false)}
                        >
                            Words
                        </button>
                        <button
                            role="tab"
                            aria-selected={props.showGraph}
                            className={segButton(props.showGraph)}
                            onClick={() => props.setShowGraph(true)}
                        >
                            Timeline
                        </button>
                    </div>
                </div>

                {!props.showGraph ? (
                    props.displayKeywords.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                            {inline.map((k) => (
                                <KeywordChip
                                    key={k.word}
                                    k={k}
                                    onClick={() => props.showKeywordContext(k.transcript_id)}
                                />
                            ))}
                            {overflow > 0 ? (
                                <button
                                    type="button"
                                    onClick={() => props.setShowDialog(true)}
                                    className="inline-flex cursor-pointer items-center rounded-full bg-tiilt-line/40 px-2.5 py-1 text-xs font-semibold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                                >
                                    +{overflow} more
                                </button>
                            ) : null}
                        </div>
                    ) : (
                        <div className="rounded-lg bg-tiilt-ground/60 px-3 py-2 text-xs text-tiilt-muted">
                            {configured
                                ? "None of this session's keywords (" +
                                  props.session.keywords.join(", ") +
                                  ") came up in this discussion."
                                : "No keywords were configured for this session, so there is nothing to detect."}
                        </div>
                    )
                ) : null}

                {props.showGraph ? (
                    configured ? (
                        <div className="flex flex-col gap-1">
                            {props.session.keywords.map((keyword) => (
                                <div key={keyword} className="flex items-center gap-3">
                                    <div
                                        className="w-24 flex-none truncate text-xs text-tiilt-muted"
                                        title={keyword}
                                    >
                                        {keyword}
                                    </div>
                                    <div className="relative h-6 w-[240px] flex-none">
                                        <div className="absolute top-1/2 right-0 left-0 border-t border-tiilt-line" />
                                        {(props.keywordPoints[keyword] || []).map(
                                            (point, index) => (
                                                <button
                                                    key={index}
                                                    type="button"
                                                    title={`"${point.word}" — open in transcript`}
                                                    className="absolute top-1/2 h-3 w-3 -translate-y-1/2 cursor-pointer rounded-full border border-white/60 transition hover:scale-125"
                                                    style={{
                                                        left: `${point.x - 6}px`,
                                                        backgroundColor: point.color,
                                                    }}
                                                    onClick={() =>
                                                        props.showKeywordContext(point.transcript_id)
                                                    }
                                                />
                                            ),
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="rounded-lg bg-tiilt-ground/60 px-3 py-2 text-xs text-tiilt-muted">
                            No keywords were configured for this session, so there is no
                            timeline to draw.
                        </div>
                    )
                ) : null}
            </div>

            <DialogBox
                show={props.showDialog}
                heading={"All detected keywords"}
                message={
                    <div className="flex flex-wrap gap-1.5">
                        {props.displayKeywords.map((k) => (
                            <KeywordChip
                                key={k.word}
                                k={k}
                                onClick={() => props.showKeywordContext(k.transcript_id)}
                            />
                        ))}
                    </div>
                }
                closedialog={() => props.setShowDialog(false)}
            />
        </>
    )
}

export { AppKeywordsPage }
