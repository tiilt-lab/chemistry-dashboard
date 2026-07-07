import { GenericDialogBox, DialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import { dlgInput, dlgPrimary } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import style from "./student-dashboard.module.css"
import style2 from "../pod-details/pod.module.css"
import React from "react"
import { AppInfographicsSessionComparison } from "../components/infographics-view/infographics_session-comparison"
import { TranscriptsComponentClient } from "../transcripts/transcripts-component_client"
import { CollaborationFeedbackDashboard } from "../components/reflection-dashboard-view/reflection-interactive-dashboard"
import {SurveyCompletion} from "./survey-question"

import MicIcon from "../Icons/Mic"
import Camera from "../Icons/Camera"
import Chevron from "../Icons/Chevron"
import { StatusPill } from "../components/status-pill"

// Same spreadsheet language as the instructor pages.
const thCls =
    "sticky top-0 bg-tiilt-ground px-4 py-2.5 text-left font-semibold whitespace-nowrap text-tiilt-ink"
const fmtSessionDate = (s) =>
    new Date(s.creation_date).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
    })
const fmtMins = (secs) =>
    secs > 0 ? `${Math.round(secs / 60)} min` : "—"

function StudentSessionDashboardPages(props) {

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
                    <div role="main" className="main-container">
                        <Appheader
                            title={props.pageTitle}
                            leftText={false}
                            rightText={""}
                            nav={() => (props.handleBack ? props.handleBack() : props.navigateToLogin())}
                        />

                        {props.nextPage === "reportoptionpage" && (
                            <React.Fragment>
                                <div className={pageShell}>
                                <div className={formCard}>
                                <div className="mx-auto flex w-full max-w-md grow flex-col gap-4 overflow-y-auto px-4 py-6">
                                    <p className="text-sm text-tiilt-muted">
                                        Enter your username to see all of your
                                        discussion sessions and reflections.
                                    </p>
                                    <div>
                                        <label htmlFor="username" className="mb-1.5 block text-sm font-semibold text-tiilt-ink">
                                            Username
                                        </label>
                                        <input
                                            id="username"
                                            className={dlgInput}
                                            placeholder="Your username"
                                            autoFocus
                                            onKeyDown={(e) => {
                                                if (e.key === "Enter")
                                                    props.loadDashboard(e.target.value.trim())
                                            }}
                                        />
                                    </div>
                                </div>
                                <div className="w-full flex-none border-t border-tiilt-line bg-white">
                                    <div className="mx-auto w-full max-w-md px-4 py-4">
                                        <button
                                            className={dlgPrimary + " w-full"}
                                            onClick={() =>
                                                props.loadDashboard(
                                                    document.getElementById("username").value.trim()
                                                )
                                            }
                                        >
                                            Continue
                                        </button>
                                    </div>
                                </div>
                                </div>
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
                                

                                {props.nextPage === "sessionlistpage" && (
                                    <div className="mt-2 grow overflow-y-auto px-4 py-4">
                                        <div className="mx-auto max-w-3xl">
                                            <div className="mb-3 text-sm text-tiilt-muted">
                                                Your sessions — open one to see your
                                                groups and reflections.
                                            </div>
                                            <div className="overflow-x-auto rounded-xl border border-tiilt-line bg-white">
                                                <table className="w-full border-collapse text-left text-sm">
                                                    <thead>
                                                        <tr className="border-b border-tiilt-line">
                                                            <th className={thCls + " w-10 text-center"}>#</th>
                                                            <th className={thCls}>Session</th>
                                                            <th className={thCls}>Date</th>
                                                            <th className={thCls + " text-right"}>Duration</th>
                                                            <th className={thCls} />
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(props.previousSessions || []).map((s, i) => (
                                                            <tr
                                                                key={s.id}
                                                                onClick={() => props.loadSelectedSessionMetrics(s)}
                                                                title={`Open ${s.name}`}
                                                                className="cursor-pointer border-t border-tiilt-line bg-white transition first:border-t-0 hover:bg-tiilt-soft/50"
                                                            >
                                                                <td className="px-4 py-2.5 text-center font-ahamono text-xs text-tiilt-muted">{i + 1}</td>
                                                                <td className="px-4 py-2.5 font-semibold text-tiilt-ink">{s.name}</td>
                                                                <td className="px-4 py-2.5 whitespace-nowrap text-tiilt-ink">{fmtSessionDate(s)}</td>
                                                                <td className="px-4 py-2.5 text-right font-ahamono tabular-nums text-tiilt-ink">{fmtMins(s.length)}</td>
                                                                <td className="px-4 py-2.5 text-right"><Chevron size={12} className="text-tiilt-muted" /></td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                                {(props.previousSessions || []).length === 0 ? (
                                                    <div className="px-4 py-6 text-center text-sm text-tiilt-muted">
                                                        No sessions found for this username yet.
                                                    </div>
                                                ) : null}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {props.nextPage === "displaygrouppage" && (
                                    <div className="mt-2 grow overflow-y-auto px-4 py-4">
                                        <div className="mx-auto max-w-3xl">
                                            <div className="mb-3 text-sm text-tiilt-muted">
                                                Your groups in this session — open one,
                                                then use Reflection Dashboard or
                                                Comparison in the sidebar.
                                            </div>
                                            <div className="overflow-x-auto rounded-xl border border-tiilt-line bg-white">
                                                <table className="w-full border-collapse text-left text-sm">
                                                    <thead>
                                                        <tr className="border-b border-tiilt-line">
                                                            <th className={thCls + " w-10 text-center"}>#</th>
                                                            <th className={thCls + " w-12"}>Type</th>
                                                            <th className={thCls}>Group</th>
                                                            <th className={thCls}>Status</th>
                                                            <th className={thCls} />
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(props.sessionDevices || []).map((device, index) => (
                                                            <tr
                                                                key={device.id}
                                                                onClick={() => props.loadSelectedSessionDeviceMetrics(device.id)}
                                                                title={`Open ${device.name}`}
                                                                className="cursor-pointer border-t border-tiilt-line bg-white transition first:border-t-0 hover:bg-tiilt-soft/50"
                                                            >
                                                                <td className="px-4 py-2.5 text-center font-ahamono text-xs text-tiilt-muted">{index + 1}</td>
                                                                <td className="px-3 py-2.5">
                                                                    <span
                                                                        title={device.has_video ? "Video pod" : "Audio-only pod"}
                                                                        className="flex h-9 w-9 flex-none items-center justify-center rounded-md bg-tiilt-soft text-tiilt-muted"
                                                                    >
                                                                        {device.has_video ? (
                                                                            <Camera />
                                                                        ) : (
                                                                            <svg width="18" height="28" viewBox="0 0 17 27">
                                                                                <MicIcon fill="currentColor" />
                                                                            </svg>
                                                                        )}
                                                                    </span>
                                                                </td>
                                                                <td className="px-4 py-2.5 font-semibold text-tiilt-ink">{device.name}</td>
                                                                <td className="px-4 py-2.5">
                                                                    {device.posthoc_analyzed_date ? (
                                                                        <StatusPill tone="teal" dot className="text-[11px]">Analyzed</StatusPill>
                                                                    ) : (
                                                                        <StatusPill tone="neutral" className="text-[11px]">Not analyzed yet</StatusPill>
                                                                    )}
                                                                </td>
                                                                <td className="px-4 py-2.5 text-right"><Chevron size={12} className="text-tiilt-muted" /></td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                                {(props.sessionDevices || []).length === 0 ? (
                                                    <div className="px-4 py-6 text-center text-sm text-tiilt-muted">
                                                        No groups found for you in this session.
                                                    </div>
                                                ) : null}
                                            </div>
                                        </div>
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
                                                        mode="student"
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


            <GenericDialogBox onClose={props.closeDialog}
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
                ))}
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


