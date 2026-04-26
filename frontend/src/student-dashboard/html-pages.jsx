import { GenericDialogBox, DialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import style from "./student-dashboard.module.css"
import style2 from "../pod-details/pod.module.css"
import style5 from "../sessions/sessions.module.css"
import React from "react"
import Select from "react-select"
import { AppInfographicsSessionComparison } from "../components/infographics-view/infographics_session-comparison"
import { TranscriptsComponentClient } from "../transcripts/transcripts-component_client"
import { CollaborationFeedbackDashboard } from "../components/reflection-dashboard-view/reflection-interactive-dashboard-student"
import {SurveyCompletion} from "./survey-question"

import MicIcon from "../Icons/Mic"

function StudentSessionDashboardPages(props) {
    const POD_ON_COLOR = "#FF6655"
    const POD_OFF_COLOR = "#D0D0D0"
    const GLOW_COLOR = "#ffc3bd"

    return (
        <>
            {(props.currentForm === "gottoselectedtranscript" &&
                Object.keys(props.currentTranscript) && (
                    <TranscriptsComponentClient
                        sessionDevice={props.sessionDevices.find((dev) => dev.id === props.selectedSessionDeviceId1)}
                        transcriptIndex={props.currentTranscript.id}
                        setParentCurrentForm={props.setCurrentForm}
                    />
                )) ||
                (props.currentForm === "gototranscript" && (
                    <TranscriptsComponentClient
                        sessionDevice={props.sessionDevices.find((dev) => dev.id === props.selectedSessionDeviceId1)}
                        transcriptIndex={undefined}
                        setParentCurrentForm={props.setCurrentForm}
                    />
                )) || (
                    <div className="main-container">
                        <Appheader
                            title={props.pageTitle}
                            leftText={false}
                            rightText={""}
                            ightEnabled={false}
                            nav={props.sessiontype === "previoussessions"? () => props.navBackTo() : () => props.navigateToLogin()}
                        />

                        {props.nextPage === "reportoptionpage" && (
                            <React.Fragment>
                                <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                    <div>

                                        <div>Session Preference:</div>
                                        <select
                                            id="preference"
                                            className="dropdown small-section"
                                            value={props.sessiontype}
                                            onChange={(e) =>
                                                props.setSessiontype(e.target.value)
                                            }
                                        >
                                            <option value="">Select Preference</option>
                                            <option value="currentsession">Current Session</option>
                                            <option value="previoussessions">Previous Sessions</option>
                                        </select>

                                        <div>User Name:</div>
                                        <input
                                            className="text-box small-section"
                                            id="username"
                                            placeholder=""
                                        />
                                        {props.sessiontype === "currentsession" ? (
                                            <>
                                                <div>Passcode:</div>
                                                <input
                                                    className="text-box small-section"
                                                    id="passcode"
                                                    value={props.pcode}
                                                    placeholder="Passcode (4 characters)"
                                                    onInput={(event) => props.changeTouppercase(event)}
                                                />
                                                {props.wrongInput
                                                    ? "Your password must be 4 characters long."
                                                    : ""}
                                            </>
                                        ) : (
                                            <></>
                                        )}

                                    </div>
                                    <button
                                        className="wide-button"
                                        onClick={() =>
                                            props.loadDashboard(
                                                document.getElementById("preference").value.trim(),
                                                document.getElementById("username").value.trim()
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
                                {props.sessiontype === "previoussessions" && (
                                    <AppSessionToolbar
                                        session={props.session}
                                        closingSession={props.onSessionClosing}

                                        menus={props.pathToSurveyOptions !== "survey" ? [
                                            {
                                                title: "Comparison",
                                                action: () => props.viewComparison(),
                                            },
                                            {
                                                title: "Reflection Dashboard",
                                                action: () => props.loadReflectiondashboard("Reflection Dashboard"),
                                            }
                                        ]: []}
                                        participants={[]}

                                        seesions={props.previousSessions.map((session, index) => (
                                            {
                                                title: session.name + ": " + new Date(session.creation_date).toDateString(),
                                                action: () => props.loadSelectedSessionMetrics(session),
                                            }
                                        ))}

                                    />
                                )}
                                

                                {props.nextPage === "displaygrouppage" && (
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
                                )}

                                {props.nextPage === "Reflection Dashboard" && props.pathToSurveyOptions !== "survey" && (
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
                                                        sessionNameForReflecDashboard={props.sessionNameForReflecDashboard}
                                                        groupNameForReflecDashboard={props.groupNameForReflecDashboard}
                                                        llmSessionAnalysis={props.selectedLLMAnalysis}
                                                        selectedSynthesizedData={props.selectedSynthesizedData}
                                                        interactivePromptFnc={props.interactivePromptFnc}
                                                        promptResponses={props.promptResponses}
                                                        isThinking={props.isThinking}
                                                        setIsThinking={props.setIsThinking}
                                                        previousSessions={props.previousSessions}
                                                        getSessionDevices={props.getSessionDevices}
                                                        selectedSessionId1={props.selectedSessionId1}
                                                        selectedSessionDeviceId1={props.selectedSessionDeviceId1}
                                                        selectFilteredDevice1={props.selectFilteredDevice1}
                                                        setdeviceIDRefectionDashboard={props.setdeviceIDRefectionDashboard}
                                                        selectedMomentIdAndIndex={props.selectedMomentIdAndIndex}
                                                        setSelectedMomentIdAndIndex={props.setSelectedMomentIdAndIndex}
                                                        loadReflectionDashboardForNewSelection={props.loadReflectionDashboardForNewSelection}
                                                        surveyquestion = {props.surveyquestion}
                                                        likertOptions = {props.likertOptions}
                                                        completedCount = {props.completedCount}
                                                        ratings = {props.ratings}
                                                        handleRate = {props.handleRate}
                                                        handleSubmit ={props.handleSubmit}
                                                        submitted ={props.submitted}
                                                        setNotes ={props.setNotes}
                                                        notes = {props.notes}
                                                        surveyAlreadyCompleted = {props.surveyAlreadyCompleted}
                                                    />

                                                ) : (
                                                    <></>
                                                )}
                                            </>

                                        )}
                                    </div>
                                )}

                                {props.nextPage === "displayreportpage" && props.pathToSurveyOptions === "survey" && (
                                    <div className="center-column-container">
                                    <SurveyCompletion
                                        surveyquestion = {props.surveyquestion}
                                        likertOptions = {props.likertOptions}
                                        completedCount = {props.completedCount}
                                        ratings = {props.ratings}
                                        handleRate = {props.handleRate}
                                        handleSubmit ={props.handleSubmit}
                                        submitted ={props.submitted}
                                        setNotes ={props.setNotes}
                                        notes = {props.notes}
                                        surveyAlreadyCompleted = {props.surveyAlreadyCompleted}
                                    />
                                    </div>
                                )}

                                {props.nextPage === "displayreportpage" && props.pathToSurveyOptions !== "survey" && (
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
                                )}
                            </div>
                        )}

                    </div>
                )}


            <GenericDialogBox
                show={
                    props.currentForm !== "" &&
                    props.currentForm !== "gottoselectedtranscript" &&
                    props.currentForm !== "gototranscript"
                }
                optionsCase={props.currentForm === "Options"}
            >
                {(props.currentForm === "Transcript" && (
                    <div className={style2["dialog-content"]}>
                        <div className={style2["dialog-heading"]}>
                            Transcript
                        </div>
                        <div className={style2["dialog-body"]}>
                            {props.currentTranscript.transcript}
                        </div>
                        <div className={style2["dialog-button-container"]}>
                            <button
                                className={`${style2["dialog-button"]} ${style2["right-button"]}`}
                                onClick={props.closeDialog}
                            >
                                Close
                            </button>
                            <button
                                className={`${style2["dialog-button"]} ${style2["left-button"]}`}
                                onClick={props.seeAllTranscripts}
                            >
                                View All
                            </button>
                        </div>
                    </div>
                )) || props.currentForm === "Transcript" && (
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
                )}
            </GenericDialogBox>
            <DialogBox
                itsclass={"add-dialog"}
                heading={props.dialogHeading}
                message={props.alertMessage}
                show={props.showAlert}
                closedialog={props.closeAlert}
            />
        </>
    )
}

export { StudentSessionDashboardPages }


