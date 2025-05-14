import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppFeaturesComponent } from "../../features/features-component"
import { AppRadarComponent } from "../../radar/radar-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import React from "react"

function AppInfographicsComparison(props) {
    return (
        <>
            {props.speakers && (
                <div className="infographics-container">
                    {props.details !== "Group" && (
                        <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
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
                                <option value="-1">Group</option>
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
                                    <option value="-1">Group</option>
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
                        props.showBoxes[0]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"wide-section"}
                                heading={"Timeline control"}
                            >
                                <AppTimelineSlider
                                    id="timeSlider"
                                    inputChanged={props.setRange}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[1]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"small-section"}
                                heading={"Discussion timeline"}
                            >
                                <AppTimeline
                                    clickedTimeline={props.onClickedTimeline}
                                    session={props.session}
                                    transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[1]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"small-section"}
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
                                type={"small-section"}
                                heading={"Keyword detection"}
                            >
                                <AppKeywordsComponent
                                    session={props.session}
                                    sessionDevice={props.sessionDevice}
                                    transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
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
                                type={"small-section"}
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
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"small-section"}
                                heading={`Participation and Impact Style`}
                            >
                                <AppIndividualFeaturesComponent
                                    session={props.session}
                                    transcripts={props.displayTranscripts}
                                    spkrId={props.selectedSpkrId1}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.details === "Comparison" &&
                        props.showBoxes.length > 0 &&
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"small-section"}
                                heading={`Participation and Impact Style`}
                            >
                                <AppIndividualFeaturesComponent
                                    session={props.session}
                                    transcripts={props.displayTranscripts}
                                    spkrId={props.selectedSpkrId2}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[3]["clicked"] && (
                            <AppSectionBoxComponent
                                type={"small-section"}
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
                                type={"small-section"}
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
                                type={"small-section"} 
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
                                type={"small-section"}
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
