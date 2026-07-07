import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { TranscriptPanel } from "../transcript-panel/transcript-panel"
import { VideoAnalyticsPanel } from "../video-analytics/video-analytics-panel"
import { ConversationDynamicsPanel } from "../conversation-dynamics/conversation-dynamics-panel"
import { DiscussionSummaryPanel } from "../discussion-summary/discussion-summary-panel"
import { StudentLongitudinalPanel } from "../student-longitudinal/student-longitudinal-panel"
import { VideoPlayer } from "../video-player/video-player"
import { PosthocTrigger } from "../posthoc/posthoc-trigger"
import { ModelNote } from "../model-note/model-note"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppFeaturesComponent } from "../../features/features-component"
import { AppRadarComponent } from "../../radar/radar-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { AppIndividualVideoFeaturesComponent } from "../individualVideometrics/video-features-component"
import React, { useState, useEffect } from "react"
import { ApiService } from "../../services/api-service"

function AppInfographicsComparison(props) {
    // Shared selection linking the transcript with the Expression & Thinking
    // Style graphs. It is the start_time of the selected utterance, which maps
    // 1:1 to a point on each feature graph.
    const [selectedTime, setSelectedTime] = useState(null)
    // Session-relative playhead of the discussion video, so the transcript can
    // follow along while it plays.
    const [playbackTime, setPlaybackTime] = useState(null)

    // Deployment-wide model registry from /api/v1/models (the audio/video
    // services' live config). Used only as the FALLBACK: every module note in
    // this view prefers the pod's own per-run provenance (posthoc_models,
    // stamped when its analysis completed), so labels describe the models
    // that actually produced the STORED rows, not whatever the deployment
    // would use today.
    const [globalModels, setGlobalModels] = useState(null)
    // Label registry mirroring routes/callback.py, keyed by provenance field.
    const PROVENANCE_LABELS = {
        asr: {
            "google-cloud-speech": "Google Cloud Speech-to-Text (video model, en-US)",
            whisper: "Whisper (open, offline)",
            whisperx: "WhisperX (open; batched + word-level alignment)",
            qwen3: "Qwen3-ASR 1.7B + ForcedAligner (open)",
            "qwen3-0.6b": "Qwen3-ASR 0.6B + ForcedAligner (open, fast)",
        },
        scorer: {
            liwc: "the LIWC & Harvard General Inquirer lexicons",
            open: "the Harvard General Inquirer lexicon (open)",
            llm: "Google Gemini (LLM contextual scoring)",
        },
        embedder: {
            "all-mpnet-base-v2": "MPNet sentence embedder (all-mpnet-base-v2)",
            "bge-large-en-v1.5": "BGE large v1.5 (open SOTA)",
        },
        keywords: {
            word2vec: "word2vec semantic matching (GoogleNews-300)",
            embedding: "SentenceTransformer semantic matching (BGE, open)",
        },
        emotion: {
            resmasking: "ResMaskingNet (FER-2013, 7 emotions)",
            hsemotion: "HSEmotion EfficientNet-B2 (AffectNet-8, open SOTA)",
        },
        attention: {
            gazefollow: "Attended-visual-targets gaze model (Chong et al. 2020, GazeFollow) + YOLOv5m head detector",
            gazelle: "Gaze-LLE (Meta 2024, DINOv2; open SOTA) + YOLOv5m head detector",
        },
        objects: {
            yolov4: "YOLOv4-P7 object detector (COCO)",
            yolo11: "YOLO11m object detector (COCO, open SOTA)",
        },
    }
    // /api/v1/models module key -> posthoc_models provenance key.
    const MODULE_TO_PROVENANCE = {
        transcription: "asr",
        scoring: "scorer",
        participation: "embedder",
        keywords: "keywords",
        emotion: "emotion",
        attention: "attention",
        objects: "objects",
    }
    const podModels =
        props.sessionDevice && props.sessionDevice.posthoc_models
    // Same shape as /api/v1/models, resolved provenance-first, so children
    // (VideoAnalyticsPanel etc.) inherit correct labels unchanged.
    const models = (() => {
        const out = { ...(globalModels || {}) }
        for (const [module, field] of Object.entries(MODULE_TO_PROVENANCE)) {
            const id = podModels && podModels[field]
            if (id) {
                out[module] = { id, label: PROVENANCE_LABELS[field][id] || id }
            }
        }
        return out
    })()
    const transcriptionLabel =
        models.transcription && models.transcription.label
    const scoringLabel = models.scoring && models.scoring.label
    useEffect(() => {
        new ApiService()
            .httpRequestCall("api/v1/models", "GET", {})
            .then((r) => (r.status === 200 ? r.json() : null))
            .then((d) => d && setGlobalModels(d))
            .catch(() => {})
    }, [])

    return (
        <>
            {props.speakers && (
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
                    {props.details !== "Group" &&
                        props.details !== "Individual" && (
                            <div className="flex w-full flex-col gap-2 @sm:flex-row">
                                <select
                                    id="speaker1"
                                    className="dropdown small-section"
                                    value={props.selectedSpkrId1}
                                    onChange={(e) =>
                                        props.setSelectedSpkrId1(
                                            parseInt(e.target.value, 10),
                                        )
                                    }
                                >
                                    <option value="-1">
                                        Select Participant
                                    </option>
                                    {props.speakers.map((speaker) => (
                                        <option
                                            key={speaker["id"]}
                                            value={speaker["id"]}
                                        >
                                            {speaker["alias"]}
                                        </option>
                                    ))}
                                </select>

                                {props.details === "Comparison" && (
                                    <select
                                        id="speaker2"
                                        className="dropdown small-section"
                                        value={props.selectedSpkrId2}
                                        onChange={(e) =>
                                            props.setSelectedSpkrId2(
                                                parseInt(e.target.value, 10),
                                            )
                                        }
                                    >
                                        <option value="-1">
                                            Select Participant
                                        </option>
                                        {props.speakers.map((speaker) => (
                                            <option
                                                key={speaker["id"]}
                                                value={speaker["id"]}
                                            >
                                                {speaker["alias"]}
                                            </option>
                                        ))}
                                    </select>
                                )}
                            </div>
                        )}
                    {props.showBoxes.length > 0 &&
                        (props.showBoxes[0]["clicked"] ||
                            props.showBoxes[1]["clicked"]) && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Session timeline"}
                            >
                                {props.showBoxes[0]["clicked"] && (
                                    <div className="mb-4">
                                        <div className="mb-2 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                            Adjust time range
                                        </div>
                                        <AppTimelineSlider
                                            id="timeSlider"
                                            inputChanged={props.setRange}
                                        />
                                    </div>
                                )}
                                {props.showBoxes[1]["clicked"] && (
                                    <AppTimeline
                                        clickedTimeline={
                                            props.onClickedTimeline
                                        }
                                        session={props.session}
                                        transcripts={
                                            props.details === "Group"
                                                ? props.displayTranscripts
                                                : props.spkr1Transcripts
                                        }
                                        start={props.startTime}
                                        end={props.endTime}
                                    />
                                )}
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Group" && props.sessionDevice && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"Session video & transcript"}
                        >
                            <div className="flex w-full flex-col gap-3">
                                <VideoPlayer
                                    sessionId={props.session.id}
                                    sessionDeviceId={props.sessionDevice.id}
                                    selectedTime={selectedTime}
                                    transcripts={props.displayTranscripts}
                                    onPlaybackTime={setPlaybackTime}
                                />
                                <TranscriptPanel
                                    transcripts={props.displayTranscripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                    onOpenFull={props.seeAllTranscripts}
                                    selectedTime={selectedTime}
                                    onSelectTime={setSelectedTime}
                                    playbackTime={playbackTime}
                                    compact
                                    transcriptionLabel={transcriptionLabel}
                                />
                            </div>
                        </AppSectionBoxComponent>
                    )}

                    {props.details === "Group" && props.sessionDevice && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"Conversation dynamics"}
                        >
                            <ConversationDynamicsPanel
                                sessionId={props.session.id}
                                sessionDeviceId={props.sessionDevice.id}
                            />
                        </AppSectionBoxComponent>
                    )}

                    {props.details === "Group" && props.sessionDevice && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"AI discussion summary"}
                        >
                            <DiscussionSummaryPanel
                                sessionId={props.session.id}
                                sessionDeviceId={props.sessionDevice.id}
                            />
                        </AppSectionBoxComponent>
                    )}

                    {props.details !== "Comparison" &&
                        (props.details === "Group"
                            ? props.displayVideoMetrics
                            : props.spkr1VideoMetrics) &&
                        (props.details === "Group"
                            ? props.displayVideoMetrics.length
                            : props.spkr1VideoMetrics.length) > 0 && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Video analytics"}
                            >
                                <VideoAnalyticsPanel
                                    videometrics={
                                        props.details === "Group"
                                            ? props.displayVideoMetrics
                                            : props.spkr1VideoMetrics
                                    }
                                    start={props.startTime}
                                    end={props.endTime}
                                    models={models}
                                    playbackTime={playbackTime}
                                    onSeek={setSelectedTime}
                                    sessionId={props.session.id}
                                    sessionDeviceId={props.sessionDevice.id}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details !== "Comparison" &&
                        !(props.details === "Group" && props.sessionDevice) && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"Transcript"}
                        >
                            <TranscriptPanel
                                transcripts={
                                    props.details === "Group"
                                        ? props.displayTranscripts
                                        : props.spkr1Transcripts
                                }
                                start={props.startTime}
                                end={props.endTime}
                                onOpenFull={props.seeAllTranscripts}
                                selectedTime={selectedTime}
                                onSelectTime={setSelectedTime}
                                playbackTime={playbackTime}
                                transcriptionLabel={transcriptionLabel}
                            />
                        </AppSectionBoxComponent>
                    )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[1]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Session timeline"}
                            >
                                <AppTimeline
                                    clickedTimeline={props.onClickedTimeline}
                                    session={props.session}
                                    transcripts={props.spkr2Transcripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details !== "Group" &&
                        props.details !== "Comparison" &&
                        props.getSpeakerAliasFromID(props.selectedSpkrId1) && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Participation across sessions"}
                            >
                                <StudentLongitudinalPanel
                                    username={props.getSpeakerAliasFromID(
                                        props.selectedSpkrId1,
                                    )}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details !== "Group" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[11]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Visual Analytics`}
                            >
                                {(props.spkr1VideoMetrics || []).length > 0 && (
<div className="mb-2 flex flex-col gap-0.5">
                                    <ModelNote label={models && models.attention && models.attention.label} fallback="Gaze-LLE (DINOv2, open SOTA) + YOLOv5m head detector" />
                                    <ModelNote label={models && models.emotion && models.emotion.label} fallback="HSEmotion EfficientNet-B2 (AffectNet-8)" />
                                    <ModelNote label={models && models.objects && models.objects.label} fallback="YOLO11m object detector (COCO)" />
                                </div>
)}
                                <AppIndividualVideoFeaturesComponent
                                    session={props.session}
                                    videometrics={props.spkr1VideoMetrics}
                                    spkrId={props.getSpeakerAliasFromID(
                                        props.selectedSpkrId1,
                                    )}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[11]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Visual Analytics`}
                            >
                                {(props.spkr2VideoMetrics || []).length > 0 && (
<div className="mb-2 flex flex-col gap-0.5">
                                    <ModelNote label={models && models.attention && models.attention.label} fallback="Gaze-LLE (DINOv2, open SOTA) + YOLOv5m head detector" />
                                    <ModelNote label={models && models.emotion && models.emotion.label} fallback="HSEmotion EfficientNet-B2 (AffectNet-8)" />
                                    <ModelNote label={models && models.objects && models.objects.label} fallback="YOLO11m object detector (COCO)" />
                                </div>
)}
                                <AppIndividualVideoFeaturesComponent
                                    session={props.session}
                                    videometrics={props.spkr2VideoMetrics}
                                    spkrId={props.getSpeakerAliasFromID(
                                        props.selectedSpkrId2,
                                    )}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details !== "Group" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Participation and Impact Style`}
                            >
                                {(props.spkr1Transcripts || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote label={models && models.participation && models.participation.label} fallback="sentence-transformer semantic cohesion (all-mpnet-base-v2)" />
                                </div>
)}
                                <AppIndividualFeaturesComponent
                                    session={props.session}
                                    transcripts={props.spkr1Transcripts}
                                    spkrId={props.selectedSpkrId1}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Participation and Impact Style`}
                            >
                                {(props.spkr2Transcripts || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote label={models && models.participation && models.participation.label} fallback="sentence-transformer semantic cohesion (all-mpnet-base-v2)" />
                                </div>
)}
                                <AppIndividualFeaturesComponent
                                    session={props.session}
                                    transcripts={props.spkr2Transcripts}
                                    spkrId={props.selectedSpkrId2}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[3]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Expression and Thinking Style"}
                            >
                                <AppFeaturesComponent
                                    session={props.session}
                                    transcripts={
                                        props.details === "Group"
                                            ? props.displayTranscripts
                                            : props.spkr1Transcripts
                                    }
                                    showFeatures={props.showFeatures}
                                    selectedTime={selectedTime}
                                    onSelectTime={setSelectedTime}
                                    scoringLabel={scoringLabel}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[3]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Expression and Thinking Style`}
                            >
                                <AppFeaturesComponent
                                    session={props.session}
                                    transcripts={props.spkr2Transcripts}
                                    showFeatures={props.showFeatures}
                                    selectedTime={selectedTime}
                                    onSelectTime={setSelectedTime}
                                    scoringLabel={scoringLabel}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[4]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Radar chart"}
                            >
                                {((props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts) || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote prefix="Scored from the transcript with" label={scoringLabel} fallback="the LIWC & Harvard General Inquirer lexicons" />
                                </div>
)}
                                <AppRadarComponent
                                    session={props.session}
                                    transcripts={
                                        props.details === "Group"
                                            ? props.displayTranscripts
                                            : props.spkr1Transcripts
                                    }
                                    radarTrigger={props.radarTrigger}
                                    start={props.startTime}
                                    end={props.endTime}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[4]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Radar chart"}
                            >
                                {(props.spkr2Transcripts || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote prefix="Scored from the transcript with" label={scoringLabel} fallback="the LIWC & Harvard General Inquirer lexicons" />
                                </div>
)}
                                <AppRadarComponent
                                    session={props.session}
                                    transcripts={props.spkr2Transcripts}
                                    radarTrigger={props.radarTrigger}
                                    start={props.startTime}
                                    end={props.endTime}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}
                    {props.showBoxes.length > 0 &&
                        props.showBoxes[2]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Keyword detection"}
                            >
                                {((props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts) || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote prefix="Matched with" label={models && models.keywords && models.keywords.label} fallback="word2vec semantic matching (GoogleNews-300)" />
                                </div>
)}
                                <AppKeywordsComponent
                                    session={props.session}
                                    sessionDevice={props.sessionDevice}
                                    transcripts={
                                        props.details === "Group"
                                            ? props.displayTranscripts
                                            : props.spkr1Transcripts
                                    }
                                    start={props.startTime}
                                    end={props.endTime}
                                    fromclient={props.fromclient}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[2]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Keyword detection"}
                            >
                                {(props.spkr2Transcripts || []).length > 0 && (
<div className="mb-2">
                                    <ModelNote prefix="Matched with" label={models && models.keywords && models.keywords.label} fallback="word2vec semantic matching (GoogleNews-300)" />
                                </div>
)}
                                <AppKeywordsComponent
                                    session={props.session}
                                    sessionDevice={props.sessionDevice}
                                    transcripts={props.spkr2Transcripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                    fromclient={props.fromclient}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Group" && props.sessionDevice && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"Re-run analysis"}
                        >
                            <PosthocTrigger
                                models={models}
                                session={props.session}
                                sessionDeviceId={props.sessionDevice.id}
                                lastAnalyzed={props.sessionDevice.posthoc_analyzed_date}
                                speakers={props.speakers}
                                transcripts={props.displayTranscripts}
                            />
                        </AppSectionBoxComponent>
                    )}
                </div>
            )}
        </>
    )
}

export { AppInfographicsComparison }
