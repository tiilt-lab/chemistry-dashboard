import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppTimeline } from "../../timeline/timeline-component"
import { AppKeywordsComponent } from "../../keywords/keywords-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { AppIndividualVideoFeaturesComponent } from "../individualVideometrics/video-features-component"
import { VideoAnalyticsPanel } from "../video-analytics/video-analytics-panel"
import { StudentLongitudinalPanel } from "../student-longitudinal/student-longitudinal-panel"

import React from "react"

function AppInfographicsSessionComparison(props) {
    return (
        <>
        <div className="infographics-container">

            {props.details === "Comparison"  && (
                <>
                    <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
                        <select
                            id="session1"
                            className="dropdown small-section"
                            value={props.selectedSessionId1}
                            onChange={(e) => props.getSessionDevices(parseInt(e.target.value, 10),"sessionOne")}
                        >
                            <option value="-1">Select Session 1</option>
                            {props.previousSessions.map((sess,index) => (
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
                                onChange={(e) => props.getSessionDevices(parseInt(e.target.value, 10),"sessionTwo")}
                            >
                                <option value="-1">Select Session 2</option>
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

                    <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
                        <select
                            id="session1"
                            className="dropdown small-section"
                            value={props.selectedSessionDeviceId1}
                            onChange={(e) => props.loadComparedSessionDeviceMetrics(parseInt(e.target.value, 10),"sessionOne")}
                        >
                            <option value="-1">Select Group 1</option>
                            {props.selectFilteredDevice1.map((device,index) => (
                                <option
                                    key={device.id}
                                    value={device.id}
                                >
                                    {device.name}
                                </option>
                            ))}
                        </select>

                        {props.details === "Comparison" && (
                            <select
                                id="speaker2"
                                className="dropdown small-section"
                                value={props.selectedSessionDeviceId2}
                                onChange={(e) => props.loadComparedSessionDeviceMetrics(parseInt(e.target.value, 10),"sessionTwo")}
                            >
                                <option value="-1">Select Group 2</option>
                            {props.selectFilteredDevice2.map((device) => (
                                <option
                                    key={device.id}
                                    value={device.id}
                                >
                                    {device.name}
                                </option>
                            ))}
                            </select>
                        )}
                    </div>
                </>

            )}
            {props.userDetail && props.userDetail.username ? (
                <AppSectionBoxComponent
                    type={"w-full"}
                    heading={"Participation across sessions"}
                >
                    <StudentLongitudinalPanel
                        username={props.userDetail.username}
                    />
                </AppSectionBoxComponent>
            ) : null}
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
                        type={"medium-section"}
                        heading={"Session timeline"}
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
                        type={"medium-section"}
                        heading={"Session timeline"}
                    >
                        <AppTimeline
                            clickedTimeline={props.onClickedTimeline}
                            session={props.session}
                            transcripts={props.session2Transcripts}
                            start={props.startTime2}
                            end={props.endTime2}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.showBoxes.length > 0 &&
                props.showBoxes[2]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
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
                        type={"medium-section"}
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

            {props.showBoxes.length > 0 &&
                props.showBoxes[9]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Visual Analytics`}
                    >
                        <VideoAnalyticsPanel
                            session={props.session}
                            videometrics={props.session1VideoMetrics}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.details === "Comparison" &&
                props.showBoxes.length > 0 &&
                props.showBoxes[9]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Visual Analytics`}
                    >
                        <VideoAnalyticsPanel
                            session={props.session}
                            videometrics={props.session2VideoMetrics}
                            spkrId={props.selectedSessionId2}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.showBoxes.length > 0 &&
                props.showBoxes[3]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
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
                props.showBoxes[3]["clicked"] && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
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

        </div>
</>
    )
}

export { AppInfographicsSessionComparison }
