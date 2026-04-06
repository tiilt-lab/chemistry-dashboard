import { GenericDialogBox, DialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import style from "./expert-rating.module.css"
import style2 from "../pod-details/pod.module.css"
import React from "react"
import Select from "react-select"
import { LikertRatingInterface } from "./left-pane"
import { AppInfographicsSessionComparison } from "../components/infographics-view/infographics_session-comparison"
import { CollaborationFeedbackDashboard } from "./reflection-interactive-dashboard-rating"
import { TranscriptsComponentClient } from "../transcripts/transcripts-component_client"
import { adjDim, isLargeScreen } from "../myhooks/custom-hooks"

import MicIcon from "../Icons/Mic"

function ExpertRatingPage(props) {
    const POD_ON_COLOR = "#FF6655"
    const POD_OFF_COLOR = "#D0D0D0"
    const GLOW_COLOR = "#ffc3bd"

    return (
        <>
            {(props.currentForm === "gottoselectedtranscript" &&
                Object.keys(props.currentTranscript) && (
                    <TranscriptsComponentClient
                        sessionDevice={props.sessionDevice}
                        transcriptIndex={props.currentTranscript.id}
                        setParentCurrentForm={props.setCurrentForm}
                    />
                )) ||
                (props.currentForm === "gototranscript" && (
                    <TranscriptsComponentClient
                        sessionDevice={props.sessionDevice}
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
                                            props.getUserParameters(
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
                                    setSelectedItemForRating={props.setSelectedItemForRating}
                                    completedCount={props.completedCount}
                                    itemsForRating={props.itemsForRating}
                                    evaluationOption={props.evaluationOption}
                                    evaluatorType={props.evaluatorType}
                                    likertOptions={props.likertOptions}
                                    ratings={props.ratings}
                                    handleRate={props.handleRate}
                                    setNotes={props.setNotes}
                                    notes={props.notes}
                                    submitted={props.submitted}
                                    handleSubmit={props.handleSubmit}
                                    loadDashboard={props.loadDashboard}
                                />

                                {props.dashboardPage === "option two dashboard" && (
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
                                                        llmSessionAnalysis={props.llmSessionAnalysis}
                                                        selectedSynthesizedData={props.synthesizedData}
                                                        interactivePromptFnc={props.interactivePromptFnc}
                                                        promptResponses={props.promptResponses}
                                                        isThinking={props.isThinking}
                                                        setIsThinking={props.setIsThinking}
                                                        selectedMomentIdAndIndex={props.selectedMomentIdAndIndex}
                                                        setSelectedMomentIdAndIndex={props.setSelectedMomentIdAndIndex}
                                                        selectedSessionId = {props.sessionId}
                                                        selectedSessionDeviceId = {props.sessionDeviceId}

                                                    />

                                                ) : (
                                                    <></>
                                                )}
                                            </>

                                        )}
                                    </div>
                                )}

                                {props.dashboardPage === "option one dashboard" && (
                                    <div className="center-column-container">
                                        {(!props.transcriptDoneLoading && !props.videoMetricDoneLoading) ? (
                                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                                <div className={style["load-text"]}>
                                                    Loading Dashboard...
                                                </div>
                                                <AppSpinner />
                                            </div>
                                        ) : (
                                            <>
                                                {props.session1Transcripts.length >= 0 || props.session1VideoMetrics.length >= 0 ? (

                                                    <AppInfographicsSessionComparison
                                                        fromclient={false}
                                                        onClickedTimeline={props.onClickedTimeline}
                                                        onClickedKeyword={props.onClickedKeyword}
                                                        session={props.session}
                                                        setRange={props.setRange}
                                                        showBoxes={props.showBoxes}
                                                        showFeatures={props.showFeatures}
                                                        startTime={props.startTime}
                                                        endTime={props.endTime}
                                                        session1Transcripts={props.session1Transcripts}
                                                        session1VideoMetrics={props.session1VideoMetrics}
                                                        details={props.details}
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
                )) ||
                    props.currentForm === "Transcript" && (
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
                heading={"Error"}
                message={props.alertMessage}
                show={props.showAlert}
                closedialog={props.closeAlert}
            />
        </>
    )
}

export { ExpertRatingPage }


