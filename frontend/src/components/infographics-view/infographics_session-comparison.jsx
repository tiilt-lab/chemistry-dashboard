import { AppSectionBoxComponent } from "../section-box/section-box-component"
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component"
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component"
import { VideoAnalyticsPanel } from "../video-analytics/video-analytics-panel"
import { StudentLongitudinalPanel } from "../student-longitudinal/student-longitudinal-panel"

import React from "react"

function AppInfographicsSessionComparison(props) {
    // Section toggles by label, not index — index gating broke every time an
    // entry was added or retired. A missing list or label means "show it".
    const boxOn = (label) => {
        const box = (props.showBoxes || []).find((b) => b.label === label)
        return !box || box.clicked
    }
    return (
        <>
        <div className="infographics-container">

            {props.details === "Comparison"  && (
                <>
                    <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
                        <select
                            id="compare-session1"
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
                                id="compare-session2"
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
                            id="compare-group1"
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
                                id="compare-group2"
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
            {boxOn("Timeline control") && (
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

            {boxOn("Video Metrics") && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Visual Analytics`}
                        badge={"gaze+facial · exploratory"}
                        badgeTone={"amber"}
                    >
                        <VideoAnalyticsPanel
                            session={props.session}
                            videometrics={props.session1VideoMetrics}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {props.details === "Comparison" &&
                boxOn("Video Metrics") && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Visual Analytics`}
                        badge={"gaze+facial · exploratory"}
                        badgeTone={"amber"}
                    >
                        <VideoAnalyticsPanel
                            session={props.session}
                            videometrics={props.session2VideoMetrics}
                            spkrId={props.selectedSessionId2}
                            showFeatures={props.showFeatures}
                        />
                    </AppSectionBoxComponent>
                )}

            {boxOn("Participation") && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Participation and Impact Style`}
                        badge={"verbal · exploratory"}
                        badgeTone={"amber"}
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
                boxOn("Participation") && (
                    <AppSectionBoxComponent
                        type={"medium-section"}
                        heading={`Participation and Impact Style`}
                        badge={"verbal · exploratory"}
                        badgeTone={"amber"}
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
