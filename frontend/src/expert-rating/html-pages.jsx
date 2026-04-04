import { GenericDialogBox, DialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import style from "./expert-rating.module.css"
import React from "react"
import Select from "react-select"
import {LikertRatingInterface} from "./left-pane"
import { AppInfographicsSessionComparison } from "../components/infographics-view/infographics_session-comparison"
import { CollaborationFeedbackDashboard } from "../components/reflection-dashboard-view/reflection-interactive-dashboard-student"
import { adjDim, isLargeScreen } from "../myhooks/custom-hooks"

import MicIcon from "../Icons/Mic"

function ExpertRatingPage(props) {
    const POD_ON_COLOR = "#FF6655"
    const POD_OFF_COLOR = "#D0D0D0"
    const GLOW_COLOR = "#ffc3bd"

    return (
        <>
            <div className="main-container">
                <Appheader
                    title={props.pageTitle}
                    leftText={false}
                    rightText={""}
                    ightEnabled={false}
                    nav={() => props.navigateToLogin()}
                />

                {props.nextPage === "reportoptionpage" && (
                    <React.Fragment>
                        <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                            <div>
                                 <div>Evaluting As:</div>
                                <select
                                    id="evaluatortype"
                                    className="dropdown small-section"
                                    value={props.evaluatorType}
                                    onChange={(e) =>
                                        props.setEvaluatorType(e.target.value)
                                    }
                                >
                                    <option value="">Select</option>
                                    <option value="student">Student</option>
                                    <option value="expert">Expert</option>
                                </select>

                                <div>Expert ID:</div>
                                <input
                                    className="text-box small-section"
                                    id="expertid-alias"
                                    placeholder="Alias/Expert Id"
                                />
                            </div>
                            <button
                                className="wide-button"
                                onClick={() =>
                                    props.loadDashboard(
                                        document.getElementById("evaluatortype").value,
                                        document.getElementById("expertid-alias").value.trim()
                                    )
                                }
                            >
                                Continue
                            </button>
                        </div>
                    </React.Fragment>
                )}

                {props.nextPage !== "reportoptionpage" && (

                    <div className="toolbar-view-container">
                            <LikertRatingInterface
                                expertDetail={props.expertDetail}
                                selectedItemForRating={props.selectedItemForRating}
                                setSelectedItemForRating = {props.setSelectedItemForRating}
                                completedCount = {props.completedCount}
                                itemsForRating = {props.itemsForRating}
                                evaluationOption = {props.evaluationOption}
                                evaluatorType = {props.evaluatorType}
                                likertOptions={props.likertOptions}
                                ratings={props.ratings}
                                handleRate={props.handleRate}
                                setNotes={props.setNotes}
                                notes = {props.notes}
                                submitted = {props.submitted}
                            />


                        {/* {props.nextPage === "displaygrouppage" && (
                            <div className="infographics-container mt-2 grow overflow-y-auto">
                                {props.sessionDevices !== null &&
                                    props.sessionDevices.length === 0 ? (
                                    <div className={style["load-text"]}>
                                        {" "}
                                        No Group found
                                    </div>
                                ) : (
                                    <></>
                                )}
                                {props.sessionDevices.length > 0 ? (
                                    props.sessionDevices.map((device, index) => (
                                        <div
                                            key={index}
                                            onClick={() => props.loadSelectedSessionDeviceMetrics(device.id)}
                                            className={style["pod-overview-button"]}
                                        >
                                            <svg
                                                className={style["pod-overview-icon"]}
                                                width="80px"
                                                height="80px"
                                                viewBox="-40 -40 80 80"
                                            >
                                                <svg
                                                    x="-8.5"
                                                    y="-13.5"
                                                    width="17"
                                                    height="27"
                                                    viewBox="0 0 17 27"
                                                >
                                                    <MicIcon
                                                        fill={
                                                            device.connected
                                                                ? POD_ON_COLOR
                                                                : POD_OFF_COLOR
                                                        }
                                                    ></MicIcon>
                                                </svg>
                                                {device.button_pressed ? (
                                                    <svg>
                                                        <circle
                                                            className={style.svgpulse}
                                                            x="0"
                                                            y="0"
                                                            r="33.5"
                                                            fill-opacity="0"
                                                            stroke={GLOW_COLOR}
                                                        ></circle>{" "}
                                                    </svg>
                                                ) : (
                                                    <></>
                                                )}
                                                <svg>
                                                    <circle
                                                        x="0"
                                                        y="0"
                                                        r="30.5"
                                                        fillOpacity="0"
                                                        strokeWidth="3"
                                                        stroke={
                                                            device.connected
                                                                ? POD_ON_COLOR
                                                                : POD_OFF_COLOR
                                                        }
                                                    ></circle>
                                                </svg>
                                            </svg>
                                            <div>{device.name}</div>
                                        </div>
                                    ))
                                ) : (
                                    <></>
                                )}
                            </div>
                        )} */}
                        <div className="center-column-container">
                            <div>
                                 <div>Evaluting As:</div>
                                    <select
                                        id="evaluatortype"
                                        className="dropdown small-section"
                                        value={props.evaluatorType}
                                        onChange={(e) =>
                                            props.setEvaluatorType(e.target.value)
                                        }
                                    >
                                        <option value="">Select</option>
                                        <option value="student">Student</option>
                                        <option value="expert">Expert</option>
                                    </select>

                                <div>Expert ID:</div>
                                    <input
                                        className="text-box small-section"
                                        id="expertid-alias"
                                        placeholder="Alias/Expert Id"
                                    />
                            </div>
                                    <button
                                        className="wide-button"
                                        onClick={() =>
                                            props.loadDashboard(
                                                document.getElementById("evaluatortype").value,
                                                document.getElementById("expertid-alias").value.trim()
                                            )
                                        }
                                    >
                                        Continue
                                    </button>
                            
                        </div>
                        {/* {props.nextPage === "Reflection Dashboard" && (
                            <div className="center-column-container">
                                {(!props.reflectionDashboardDoneLoading) ? (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <div className={style["load-text"]}>
                                            Loading Reflection Dashboard...
                                        </div>
                                        <AppSpinner />
                                    </div>
                                ) : (
                                    <>
                                        {props.selectedSessionId1 !== -1 && (props.session1Transcripts.length >= 0 || props.session1VideoMetrics.length >= 0) ? (

                                            <CollaborationFeedbackDashboard
                                                sessionNameForReflecDashboard = {props.sessionNameForReflecDashboard}
                                                groupNameForReflecDashboard = {props.groupNameForReflecDashboard}
                                                llmSessionAnalysis={props.selectedLLMAnalysis}
                                                selectedSynthesizedData={props.selectedSynthesizedData}
                                                interactivePromptFnc={props.interactivePromptFnc}
                                                promptResponses={props.promptResponses}
                                                isThinking={props.isThinking}
                                                setIsThinking={props.setIsThinking}
                                                previousSessions={props.previousSessions}
                                                getSessionDevices={props.getSessionDevices}
                                                selectedSessionId1={props.selectedSessionId1}
                                                selectedSessionDeviceId1 = {props.selectedSessionDeviceId1}
                                                selectFilteredDevice1={props.selectFilteredDevice1}
                                                setdeviceIDRefectionDashboard={props.setdeviceIDRefectionDashboard}
                                                selectedMomentIdAndIndex={props.selectedMomentIdAndIndex}
                                                setSelectedMomentIdAndIndex={props.setSelectedMomentIdAndIndex} 
                                                loadReflectionDashboardForNewSelection = {props.loadReflectionDashboardForNewSelection}
                                            />

                                        ) : (
                                            <></>
                                        )}
                                    </>

                                )}
                            </div>
                        )} */}

                        {/* {props.nextPage === "displayreportpage" && (
                            <div className="center-column-container">
                                {(!props.transcriptDoneLoading && !props.videoMetricDoneLoading) ? (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                        <div className={style["load-text"]}>
                                            Loading Session Data...
                                        </div>
                                        <AppSpinner />
                                    </div>
                                ) : (
                                    <>
                                        {props.selectedSessionId1 !== -1 && (props.session1Transcripts.length >= 0 || props.session1VideoMetrics.length >= 0) ? (

                                            <AppInfographicsSessionComparison
                                                displayTranscripts={props.displayTranscripts}
                                                displayVideoMetrics={props.displayVideoMetrics}
                                                fromclient={false}
                                                onClickedTimeline={props.onClickedTimeline}
                                                radarTrigger={props.radarTrigger}
                                                session={props.session}
                                                sessionDevice={props.sessionDevice}
                                                setRange={props.setRange}
                                                showBoxes={props.showBoxes}
                                                showFeatures={props.showFeatures}
                                                startTime={props.startTime}
                                                endTime={props.endTime}
                                                startTime2={props.startTime2}
                                                endTime2={props.endTime2}
                                                previousSessions={props.previousSessions}
                                                selectedSessionId1={props.selectedSessionId1}
                                                setSelectedSessionId1={props.setSelectedSessionId1}
                                                selectedSessionId2={props.selectedSessionId2}
                                                setSelectedSessionId2={props.setSelectedSessionId2}
                                                session1Transcripts={props.session1Transcripts}
                                                session2Transcripts={props.session2Transcripts}
                                                session1VideoMetrics={props.session1VideoMetrics}
                                                session2VideoMetrics={props.session2VideoMetrics}
                                                details={props.details}
                                                userDetail={props.userDetail}
                                                loadComparedSessionMetrics={props.loadComparedSessionMetrics}
                                                selectFilteredDevice1={props.selectFilteredDevice1}
                                                selectFilteredDevice2={props.selectFilteredDevice2}
                                                selectedSessionDeviceId1={props.selectedSessionDeviceId1}
                                                selectedSessionDeviceId2={props.selectedSessionDeviceId2}
                                                getSessionDevices={props.getSessionDevices}
                                                loadComparedSessionDeviceMetrics={props.loadComparedSessionDeviceMetrics}
                                            ></AppInfographicsSessionComparison>

                                        ) : (
                                            <></>
                                        )}
                                    </>

                                )}
                            </div>
                        )} */}
                    </div>
                )}

            </div>


            <GenericDialogBox
                show={props.currentForm !== ""}
                optionsCase={props.currentForm === "Options"}
            >
                {props.currentForm === "Transcript" ? (
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>
                            Transcript
                        </div>
                        <div className={style["dialog-body"]}>
                            {props.currentTranscript.transcript}
                        </div>
                        <div className={style["dialog-button-container"]}>
                            <button
                                className={`${style["dialog-button"]} ${style["right-button"]}`}
                                onClick={props.closeDialog}
                            >
                                Close
                            </button>
                            <button
                                className={`${style["dialog-button"]} ${style["left-button"]}`}
                                onClick={props.seeAllTranscripts}
                            >
                                View All
                            </button>
                        </div>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>
            <DialogBox
                itsclass={"add-dialog"}
                heading={"Error"}
                message={props.alertMessage}
                show={props.showAlert}
                closedialog={props.closeAlert}
            />
        </>
    )
}

export { ExpertRatingPage }


