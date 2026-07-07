import { GenericDialogBox, WaitingDialog } from "../dialog/dialog-component"
import { ErrorDialog } from "../components/error-dialog"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { Appheader } from "../header/header-component"
import style from "./pod.module.css"
import React from "react"
import Select from "react-select"
import { AppInfographicsComparison } from "../components/infographics-view/infographics-comparison"
import { CollaborationFeedbackDashboard } from "../components/reflection-dashboard-view/reflection-interactive-dashboard"

function PodComponentPages(props) {
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={
                        (props.session && props.session.name
                            ? props.session.name + " › "
                            : "") +
                        (props.details === "Group" ||
                        props.details === "Reflection Dashboard"
                            ? props.sessionDevice.name
                            : props.selectedSpkralias)
                    }
                    leftText={false}
                    rightText={"Options"}
                    rightTextClick={() => props.openDialog("Options")}
                    nav={props.navigateToSession}
                    escToBack={true}
                />
                <div className="toolbar-view-container">
                    {props.session ? (
                        <AppSessionToolbar
                            session={props.session}
                            closingSession={props.onSessionClosing}
                            menus={[
                                {
                                    title: "Group Overview",
                                    action: () => props.dashboardView("Group"),
                                },
                                {
                                    title: "Reflection Dashboard",
                                    action: () =>
                                        props.loadReflectiondashboard(
                                            "Reflection Dashboard",
                                        ),
                                },
                                {
                                    title: "Individual Comparison",
                                    action: () =>
                                        props.dashboardView("Comparison"),
                                },
                            ]}
                        />
                    ) : (
                        <></>
                    )}
                    <div className="center-column-container">
                        {props.details === "Reflection Dashboard" ? (
                            <CollaborationFeedbackDashboard
                                participants={props.participants}
                                currentParticipant={props.currentParticipant}
                                llmPendingFor={props.llmPendingFor}
                                llmSessionAnalysis={
                                    props.selectedParticipantLLMAnalysis
                                }
                                selectedParticipantSynthesizedData={
                                    props.selectedParticipantSynthesizedData
                                }
                                interactivePromptFnc={
                                    props.interactivePromptFnc
                                }
                                promptResponses={props.promptResponses}
                                isThinking={props.isThinking}
                                setIsThinking={props.setIsThinking}
                                setParticipantIDRefectionDashboard={
                                    props.setParticipantIDRefectionDashboard
                                }
                                selectedMomentIdAndIndex={
                                    props.selectedMomentIdAndIndex
                                }
                                setSelectedMomentIdAndIndex={
                                    props.setSelectedMomentIdAndIndex
                                }
                            />
                        ) : (
                            <AppInfographicsComparison
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
                                speakers={props.speakers}
                                selectedSpkrId1={props.selectedSpkrId1}
                                setSelectedSpkrId1={props.setSelectedSpkrId1}
                                selectedSpkrId2={props.selectedSpkrId2}
                                setSelectedSpkrId2={props.setSelectedSpkrId2}
                                spkr1Transcripts={props.spkr1Transcripts}
                                spkr2Transcripts={props.spkr2Transcripts}
                                spkr1VideoMetrics={props.spkr1VideoMetrics}
                                spkr2VideoMetrics={props.spkr2VideoMetrics}
                                details={props.details}
                                getSpeakerAliasFromID={
                                    props.getSpeakerAliasFromID
                                }
                                seeAllTranscripts={props.seeAllTranscripts}
                            ></AppInfographicsComparison>
                        )}
                    </div>
                </div>
                {props.loading(props.details) ? (
                    <AppSpinner></AppSpinner>
                ) : (
                    <></>
                )}
            </div>
            <GenericDialogBox onClose={props.closeDialog}
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

                {props.currentForm === "Options" ? (
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>
                            Section Boxes
                        </div>
                        <div className={style["dialog-dropdown"]}>
                            <Select
                                options={props.showBoxes}
                                value={props.showBoxes.filter(
                                    (feature) => feature["clicked"],
                                )}
                                onChange={props.handleCheckBoxes}
                            />
                        </div>
                        <div className={style["dialog-heading"]}>
                            Session Features
                        </div>
                        <div className={style["dialog-dropdown"]}>
                            <Select
                                options={props.showFeatures}
                                value={props.showFeatures.filter(
                                    (feature) => feature["clicked"],
                                )}
                                onChange={props.handleCheckFeats}
                            />
                        </div>
                        <div className={style["dialog-heading"]}>
                            Device Options
                        </div>
                        <button
                            className={style["basic-button"]}
                            onClick={() => props.openDialog("RemoveDevice")}
                        >
                            Disconnect Device
                        </button>
                        <button
                            className={style["cancel-button"]}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "RemoveDevice" ? (
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>
                            Disconnect Device
                        </div>
                        {!props.deleteDeviceToggle ? (
                            <React.Fragment>
                                <div className={style["dialog-body"]}>
                                    Are you sure you want to remove this device?
                                </div>
                                <div className={style["dialog-body"]}>
                                    All data will be saved, but the device will
                                    be disconnected from the session.
                                </div>
                            </React.Fragment>
                        ) : (
                            <></>
                        )}

                        {props.deleteDeviceToggle ? (
                            <React.Fragment>
                                <div className={style["dialog-body"]}>
                                    Are you sure you want to delete this device?
                                </div>
                                <div className={style["dialog-body"]}>
                                    All data for this device will be lost and
                                    the device will be disconnected.
                                </div>
                            </React.Fragment>
                        ) : (
                            <></>
                        )}
                        <label className="flex cursor-pointer items-center gap-2 py-1 text-sm text-tiilt-ink">
                            <input
                                id="cbxDelete"
                                type="checkbox"
                                className="h-4 w-4 cursor-pointer accent-tiilt"
                                checked={props.deleteDeviceToggle}
                                value={props.deleteDeviceToggle}
                                onChange={() =>
                                    props.setDeleteDeviceToggle(
                                        !props.deleteDeviceToggle,
                                    )
                                }
                            />
                            Delete device
                        </label>
                        <div className={style["dialog-button-container"]}>
                            <button
                                className={style["basic-button"]}
                                onClick={() =>
                                    props.removeDeviceFromSession(
                                        props.deleteDeviceToggle,
                                    )
                                }
                            >
                                Confirm
                            </button>
                            <button
                                className={style["cancel-button"]}
                                onClick={props.closeDialog}
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>

            {/* The AI reflection no longer blocks the page while generating —
                the dashboard shows an inline pending banner instead. */}

            <ErrorDialog
                message={props.llmError}
                show={!!props.llmError}
                onClose={props.clearLlmError}
            />
        </>
    )
}

export { PodComponentPages }

/*
<AppSectionBoxComponent heading={"Box 1:"}></AppSectionBoxComponent>

            <AppSectionBoxComponent heading={"Box 2:"}></AppSectionBoxComponent>

            <AppSectionBoxComponent heading={"Box 3:"}></AppSectionBoxComponent>
*/
