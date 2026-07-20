// Voice-print state + quality display, shared by the Students roster
// (enrollment dialog) and the student profile page.

// Voice-print state from the enrollment fields (the .check.json verdict the
// audio service writes at capture time / via the survey run). Three grades:
// weak = genuinely broken (near-silent or doesn't match itself); short = only
// fails the net-speech bar (old 10s-cap era — usable, but worth redoing
// eventually); ok = passes. Similarity to another voice is NOT a defect —
// overlaps are shown separately.
export function voiceState(s) {
    if (!s.voice_enrolled) return { label: "No voice", tone: "orange" }
    const c = s.voice_check
    if (!c) return { label: "Voice ✓", tone: "neutral" } // not yet checked
    const broken =
        (c.net_speech_seconds ?? 0) < 5 ||
        (c.self_similarity != null && c.self_similarity < 0.45)
    if (broken) return { label: "Voice: weak", tone: "orange" }
    if (c.ok === false) return { label: "Voice: short", tone: "neutral" }
    return { label: "Voice ✓", tone: "teal" }
}

export function enrollmentNeedsAttention(s) {
    return (
        !s.voice_enrolled ||
        !s.face_enrolled ||
        voiceState(s).label === "Voice: weak"
    )
}

// The fingerprint player + quality-check readout for one student. Renders the
// no-recording warning when there's nothing on file.
export function VoiceQualityCard({ student }) {
    if (!student.voice_enrolled)
        return (
            <div className="mb-3 rounded-md bg-tiilt-orange/15 px-3 py-2 text-xs text-tiilt-orange-text">
                No voice recording on file — this student's speech can only be
                attributed by diarization clustering.
            </div>
        )
    return (
        <>
            <audio
                controls
                preload="none"
                className="mb-3 w-full"
                src={`/api/v1/students/${student.id}/fingerprint_audio`}
            />
            {student.voice_check ? (
                <div className="mb-3 flex flex-col gap-1.5 rounded-lg bg-tiilt-ground/60 px-3 py-2 text-xs text-tiilt-ink">
                    <div className="flex items-center justify-between gap-3">
                        <span>Clear speech in the recording</span>
                        <span
                            className={
                                "font-ahamono font-semibold " +
                                ((student.voice_check.net_speech_seconds ?? 0) >= 12
                                    ? "text-tiilt-teal-text"
                                    : "text-tiilt-orange-text")
                            }
                        >
                            {student.voice_check.net_speech_seconds ?? "?"}s
                            <span className="font-normal text-tiilt-muted">
                                {" "}
                                / 12s needed
                            </span>
                        </span>
                    </div>
                    <div
                        className="flex items-center justify-between gap-3"
                        title="How well the two halves of the recording match each other. Low values mean noise or too little speech."
                    >
                        <span>Matches itself</span>
                        <span
                            className={
                                "font-ahamono font-semibold " +
                                ((student.voice_check.self_similarity ?? 0) >= 0.45
                                    ? "text-tiilt-teal-text"
                                    : "text-tiilt-orange-text")
                            }
                        >
                            {student.voice_check.self_similarity ?? "—"}
                            <span className="font-normal text-tiilt-muted">
                                {" "}
                                / 0.45 needed
                            </span>
                        </span>
                    </div>
                    <div
                        className="flex items-center justify-between gap-3"
                        title="Similarity to the closest OTHER enrolled voice. High values mean this student's speech can be confused with someone else's."
                    >
                        <span>Confusable with another voice</span>
                        <span
                            className={
                                "font-ahamono font-semibold " +
                                ((student.voice_check.nearest_other_similarity ?? 0) < 0.5
                                    ? "text-tiilt-teal-text"
                                    : "text-tiilt-orange-text")
                            }
                        >
                            {student.voice_check.nearest_other_similarity ?? "—"}
                            <span className="font-normal text-tiilt-muted">
                                {" "}
                                (0.50 = too close)
                            </span>
                        </span>
                    </div>
                    {student.voice_check.ok === false ? (
                        <div className="mt-1 rounded-md bg-tiilt-orange/15 px-2.5 py-1.5 leading-relaxed text-tiilt-orange-text">
                            {student.voice_check.message ||
                                "This recording failed the quality check."}
                        </div>
                    ) : null}
                </div>
            ) : (
                <div className="mb-3 text-xs text-tiilt-muted">
                    No quality report yet for this recording.
                </div>
            )}
        </>
    )
}
