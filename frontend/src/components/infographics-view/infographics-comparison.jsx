import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppFeaturesComponent } from "../../features/features-component"
//import { AppIndividualFeaturesComponent } from "frontend\src\individualmetrics\features-component.js"
import { AppRadarComponent } from "../../radar/radar-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import style from "../../byod-join/byod-join.module.css"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { adjDim } from "../../myhooks/custom-hooks"
import React from "react"

function AppInfographicsComparison(props) {
    return (
        <>
            {props.speakers && (
                <div className="infographics-container">
                    <select
                        id="speaker1"
                        className={style["dropdown-input"]}
                        style={{ width: adjDim(350) + "px" }}
                        value={props.selectedSpkrId1}
                        onChange={(e) =>
                            props.setSelectedSpkrId1(
                                parseInt(e.target.value, 10),
                            )
                        }
                    >
                        <option value="-1">Group</option>
                        {props.speakers.map((speaker) => (
                            <option key={speaker["id"]} value={speaker["id"]}>
                                {speaker["alias"]}
                            </option>
                        ))}
                    </select>

                    <select
                        id="speaker2"
                        className={style["dropdown-input"]}
                        style={{ width: adjDim(350) + "px" }}
                        value={props.selectedSpkrId2}
                        onChange={(e) =>
                            props.setSelectedSpkrId2(
                                parseInt(e.target.value, 10),
                            )
                        }
                    >
                        <option value="-1">Group</option>
                        {props.speakers.map((speaker) => (
                            <option key={speaker["id"]} value={speaker["id"]}>
                                {speaker["alias"]}
                            </option>
                        ))}
                    </select>
                    {props.showBoxes.length > 0 &&
                        props.showBoxes[0]["clicked"] && (
                            <AppSectionBoxComponent
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
                                heading={"Discussion timeline"}
                            >
                                <AppTimeline
                                    clickedTimeline={props.onClickedTimeline}
                                    session={props.session}
                                    transcripts={props.spkr1Transcripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[1]["clicked"] && (
                            <AppSectionBoxComponent
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
                                heading={"Keyword detection"}
                            >
                                <AppKeywordsComponent
                                    session={props.session}
                                    sessionDevice={props.sessionDevice}
                                    transcripts={props.spkr1Transcripts}
                                    start={props.startTime}
                                    end={props.endTime}
                                    fromclient={props.fromclient}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[2]["clicked"] && (
                            <AppSectionBoxComponent
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

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
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

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[5]["clicked"] && (
                            <AppSectionBoxComponent
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
                                heading={"Expression and Thinking Style"}
                            >
                                <AppFeaturesComponent
                                    session={props.session}
                                    transcripts={props.spkr1Transcripts}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[3]["clicked"] && (
                            <AppSectionBoxComponent
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
                            <AppSectionBoxComponent heading={"Radar chart"}>
                                <AppRadarComponent
                                    session={props.session}
                                    transcripts={props.spkr1Transcripts}
                                    radarTrigger={props.radarTrigger}
                                    start={props.startTime}
                                    end={props.endTime}
                                    showFeatures={props.showFeatures}
                                />
                            </AppSectionBoxComponent>
                        )}

                    {props.showBoxes.length > 0 &&
                        props.showBoxes[4]["clicked"] && (
                            <AppSectionBoxComponent heading={"Radar chart"}>
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
