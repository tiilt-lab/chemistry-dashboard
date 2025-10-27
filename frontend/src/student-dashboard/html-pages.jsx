import { GenericDialogBox, DialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import style from "./student-dashboard.module.css"
import style5 from "../sessions/sessions.module.css"
import React from "react"
import Select from "react-select"
import { AppInfographicsSessionComparison } from "../components/infographics-view/infographics_session-comparison"
import { adjDim, isLargeScreen } from "../myhooks/custom-hooks"

function StudentSessionDashboardPages(props) {
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



                {props.nextPage === "displayreportpage" && (
                    <>
                       
                        <div className="toolbar-view-container">
                            {props.sessiontype === "previoussessions" && (
                                <AppSessionToolbar
                                    session={props.session}
                                    closingSession={props.onSessionClosing}
                                    menus={[
                                        // {
                                        //     title: "Individual",
                                        //     action: () => props.viewIndividual(),
                                        // },
                                        {
                                            title: "Comparison",
                                            action: () => props.viewComparison(),
                                        },
                                    ]}
                                    participants={[]}

                                    seesions={props.previousSessions.map((session, index) => (
                                        {
                                            title: session.name + ": " + new Date(session.creation_date).toDateString(),
                                            action: () => props.loadPreviousSessionMetrics(session),
                                        }
                                    ))}

                                />
                            )}


                            {props.selectedSessionId1 !== -1 && (props.session1Transcripts.length >= 0 || props.session1VideoMetrics.length >= 0) ? (
                                <div className="center-column-container">
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
                                    ></AppInfographicsSessionComparison>
                                </div>
                            ) :
                                (
                                    <></>
                                )}

                        </div>
                    </>
                )}
            </div>


            <GenericDialogBox
                show={props.currentForm !== ""}
                optionsCase={props.currentForm == "Options"}
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

export { StudentSessionDashboardPages }


