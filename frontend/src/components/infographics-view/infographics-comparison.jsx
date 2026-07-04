import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppFeaturesComponent } from "../../features/features-component"
import { AppRadarComponent } from "../../radar/radar-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { AppIndividualVideoFeaturesComponent } from "../individualVideometrics/video-features-component"
import React from "react"

function AppInfographicsComparison(props) {
    
    return (
        <>
            {props.speakers && (
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6">
                    {props.details !== "Group" && props.details!== "Individual" && (
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
                                <option value="-1">Select Participant</option>
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
                                    <option value="-1">Select Participant</option>
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
                                        clickedTimeline={props.onClickedTimeline}
                                        session={props.session}
                                        transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                                        start={props.startTime}
                                        end={props.endTime}
                                    />
                                )}
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

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[2]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"w-full"}
                                heading={"Keyword detection"}
                            >
                                <AppKeywordsComponent
                                    session={props.session}
                                    sessionDevice={props.sessionDevice}
                                    transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts }
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
                                    spkrId={props.getSpeakerAliasFromID(props.selectedSpkrId1)}
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
                                    spkrId={props.getSpeakerAliasFromID(props.selectedSpkrId2)}
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
                                    transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                                    showFeatures={props.showFeatures}
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
                                    transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
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
                </div>
            )}
        </>
    )
}

export { AppInfographicsComparison }
