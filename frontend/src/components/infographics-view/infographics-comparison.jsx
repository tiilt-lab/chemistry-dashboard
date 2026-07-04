import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { TranscriptPanel } from "../transcript-panel/transcript-panel"
import { VideoAnalyticsPanel } from "../video-analytics/video-analytics-panel"
import { VideoPlayer } from "../video-player/video-player"
import { PosthocTrigger } from "../posthoc/posthoc-trigger"
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

    // Active transcription / scoring models, reported by the server from the
    // audio processor's live config, so labels reflect what actually ran.
    const [models, setModels] = useState(null)
    useEffect(() => {
        new ApiService()
            .httpRequestCall("api/v1/models", "GET", {})
            .then((r) => (r.status === 200 ? r.json() : null))
            .then((d) => d && setModels(d))
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
                                heading={"Discussion timeline"}
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
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Group" && props.sessionDevice && (
                        <AppSectionBoxComponent
                            type={"w-full"}
                            heading={"Discussion video"}
                        >
                            <VideoPlayer
                                sessionId={props.session.id}
                                sessionDeviceId={props.sessionDevice.id}
                                selectedTime={selectedTime}
                                transcripts={props.displayTranscripts}
                                onPlaybackTime={setPlaybackTime}
                            />
                        </AppSectionBoxComponent>
                    )}

                    {props.details !== "Comparison" && (
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
                                transcriptionLabel={models && models.transcription && models.transcription.label}
                            />
                        </AppSectionBoxComponent>
                    )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[1]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Discussion timeline"}
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
                        props.showBoxes.length > 0 &&
                        props.showBoxes[11]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={`Visual Analytics`}
                            >
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
                                    scoringLabel={models && models.scoring && models.scoring.label}
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
                                    scoringLabel={models && models.scoring && models.scoring.label}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[4]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Radar chart"}
                            >
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
                                session={props.session}
                                sessionDeviceId={props.sessionDevice.id}
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
