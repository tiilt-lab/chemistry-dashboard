import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppFeaturesComponent } from "../../features/features-component"
import { AppRadarComponent } from "../../radar/radar-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { AppIndividualVideoFeaturesComponent } from "../individualVideometrics/video-features-component"

import { AppSpinner } from "../../spinner/spinner-component"

import style from "../../student-dashboard/student-dashboard.module.css"

import React from "react"

function AppInfographicsSessionComparison(props) {
    
    return (
        <>
         {props.session1Transcripts.length <= 0 || props.session1VideoMetrics.length <=0 ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className={style["load-text"]}>
                                Loading Session Data...
                            </div>
                            <AppSpinner />
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className={style["load-text"]}>
                                Nothing Loading ...
                            </div>
                            <AppSpinner />
                        </div>
                    )}
        <div className="infographics-container">
            {props.details === "Comparison"  && (
                <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
                    <select
                        id="session1"
                        className="dropdown small-section"
                        value={props.selectedSessionId1}
                        onChange={(e) =>
                            props.setSelectedSessionId1(
                                parseInt(e.target.value, 10),
                            )
                        }
                    >
                        <option value="-1">Select Session</option>
                        {props.previousSessions.map((sess) => (
                            <option
                                key={sess.id}
                                value={sess.id}
                            >
                                {sess.name}
                            </option>
                        ))}
                    </select>

                    {props.details === "Comparison" && (
                        <select
                            id="speaker2"
                            className="dropdown small-section"
                            value={props.selectedSessionId2}
                            onChange={(e) =>
                                props.setSelectedSessionId2(
                                    parseInt(e.target.value, 10),
                                )
                            }
                        >
                            <option value="-1">Select Session</option>
                           {props.previousSessions.map((sess) => (
                            <option
                                key={sess.id}
                                value={sess.id}
                            >
                                {sess.name}
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
                            transcripts={props.session1Transcripts}
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
                            transcripts={props.session2Transcripts}
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
                            // sessionDevice={props.sessionDevice}
                            transcripts={props.session1Transcripts}
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
                            // sessionDevice={props.sessionDevice}
                            transcripts={props.session2Transcripts}
                            start={props.startTime}
                            end={props.endTime}
                            fromclient={props.fromclient}
                        />
                    </AppSectionBoxComponent>
                )}

                    {props.session1Transcripts.length <= 0 || props.session1VideoMetrics.length <=0 ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className={style["load-text"]}>
                                Loading Session Data...
                            </div>
                            <AppSpinner />
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className={style["load-text"]}>
                                Nothing Loading ...
                            </div>
                            <AppSpinner />
                        </div>
                    )}

            {props.details === "Individual" &&
                props.showBoxes.length > 0 &&
                props.showBoxes[11]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"wide-section"}
                        heading={`Visual Analytics`}
                    >
                        <AppIndividualVideoFeaturesComponent
                            session={props.session}
                            videometrics={props.session1VideoMetrics}
                            spkrId={props.selectedSessionId1}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.details === "Comparison" &&
                props.showBoxes.length > 0 &&
                props.showBoxes[11]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"small-section"}
                        heading={`Visual Analytics`}
                    >
                        <AppIndividualVideoFeaturesComponent
                            session={props.session}
                            videometrics={props.session2VideoMetrics}
                            spkrId={props.selectedSessionId2}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.details === "Individual" &&
                props.showBoxes.length > 0 &&
                props.showBoxes[5]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"small-section"}
                        heading={`Participation and Impact Style`}
                    >
                        <AppIndividualFeaturesComponent
                            session={props.session}
                            transcripts={props.session1Transcripts}
                            spkrId= "sessiontranscriptcomparison"
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
                            transcripts={props.session2Transcripts}
                            spkrId="sessiontranscriptcomparison"
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
                            transcripts={props.session1Transcripts}
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
                            transcripts={props.session2Transcripts}
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
                            transcripts={props.session1Transcripts}
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
                            transcripts={props.session2Transcripts}
                            radarTrigger={props.radarTrigger}
                            start={props.startTime}
                            end={props.endTime}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}
        </div>
</>
    )
}

export { AppInfographicsSessionComparison }
