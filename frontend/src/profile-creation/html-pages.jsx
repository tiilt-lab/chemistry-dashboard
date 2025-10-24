import React, { useState } from "react"
import { Appheader } from "../header/header-component"
import { VoiceRecorder } from "react-voice-recorder-player"
import {
    DialogBox,
    WaitingDialog,
    DialogBoxTwoOption,
    GenericDialogBox,
} from "../dialog/dialog-component"
import { AppSectionBoxComponent } from "../components/section-box/section-box-component"
import { AppSpinner } from "../spinner/spinner-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { TranscriptsComponentClient } from "../transcripts/transcripts-component_client"
import { adjDim, isLargeScreen } from "../myhooks/custom-hooks"

import style from "./profile-creation.module.css"
import style2 from "../pod-details/pod.module.css"
import style3 from "../manage-keyword-lists/manage-keyword-lists.module.css"
import style4 from "../components/context-menu/context-menu.module.css"
import style5 from "../sessions/sessions.module.css"
import MicIcon from "@icons/Mic"
import Checkmark from "@assets/img/checkmark.svg"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { AppInfographicsComparison } from "../components/infographics-view/infographics-comparison"
import {RecordingCoach} from "./recording-coach"

function ProfileCreationPage(props) {
    // console.log(props, 'props')
    return (
        <>
            {(
                <div className="main-container">
                    <Appheader
                        title={props.pageTitle}
                        leftText={false}
                        rightText={""}
                        rightEnabled={false}
                        nav={() => props.navigateToLogin()}
                    />
                    {props.nextPage === "profile_creation" && (
                        <React.Fragment>
                            <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                <div>
                                    <div className="my-1.5 font-sans text-base leading-5 font-normal text-[#727278]">
                                        Please complete the form by providing your first and last name, and username
                                    </div>
                                    <div className="my-1.5 font-sans text-xs leading-5 font-normal text-[#727278]">
                                        Your will need to record a 10 seconds video in the next page. This video will be stored to
                                        help match you voice and face during analytics
                                    </div>
                                </div>
                                <div>
                                    <div>Last Name:</div>
                                    <input
                                        className="text-box small-section"
                                        maxlength={50}
                                        id="lastname"
                                        placeholder="Last Name"
                                    />
                                    <div>First Name:</div>
                                    <input
                                        className="text-box small-section"
                                        maxLength={50}
                                        id="firstname"
                                        placeholder="First Name"
                                    />
                                    <div>User Name:</div>
                                    <input
                                        maxlength={10}
                                        minlength={5}
                                        className="text-box small-section"
                                        id="username"
                                        placeholder="Username (10 characters max)"
                                    />
                                </div>
                                <button
                                    className="wide-button"
                                    onClick={() =>
                                        props.verifyUserProfileInput(
                                            document
                                                .getElementById("lastname")
                                                .value.trim(),
                                            document
                                                .getElementById("firstname")
                                                .value.trim(),
                                            document
                                                .getElementById("username")
                                                .value.trim()
                                        )
                                    }
                                >
                                    Continue
                                </button>
                            </div>
                        </React.Fragment>
                    )}
                    {props.nextPage === "video_audio_capture_page" && (
                        <React.Fragment>
                            <RecordingCoach
                                maxDurationSec={60}
                                minDurationSec={15}
                                onTestClip={(blob, diag) => console.log('test', blob, diag)}
                                onComplete={(blob, diag) => console.log('full', blob, diag)}
                                saveRecording={props.saveRecording}
                            />
                            {/* <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto h-screen text-center">
                                <div className="w-[300px] px-2 sm:w-[400px] lg:w-3xl">
                                    <div className="my-1.5 font-sans text-base/loose font-medium text-[#727278]">
                                        Please add a Speaker Fingerprint
                                        for each speaker
                                    </div>
                                    <div className="my-1.5 font-sans text-xs/normal font-normal text-[#727278]">
                                        Each speaker must record and
                                        temporarily save a short 10
                                        second sample of their voice.
                                        This is used to track each
                                        speaker's metrics throughout a
                                        discussion and is deleted upon
                                        ending the discussion.
                                    </div>
                                </div>
                                <div className="min-w-{300px} flex h-60 flex-col items-center justify-around text-center sm:h-70">
                                    <div className="sans text-base/normal font-bold sm:text-xl/loose">
                                        Record Speaker Fingerprint:
                                    </div>
                                    {props.isRecordingStopped ?
                                        <div>

                                            <video id="video_playback" controls autoPlay muted width={500} height={500} />
                                            <button className="toolbar-button z-40" onClick={props.startRecording} >Record Again</button>
                                            <button className="toolbar-button z-40" onClick={props.saveRecording} >Save Recording</button>
                                        </div>
                                        :
                                        <div>

                                            <video id="video_preview" controls muted width={500} height={500} />
                                            <button className="toolbar-button z-40" onClick={props.startRecording} >Start Recording</button>
                                            <button className="toolbar-button z-40" onClick={props.stopRecording} >Stop Recording</button>
                                        </div>
                                    }


                                </div>
                                <div>
                                    <button
                                        className="wide-button"
                                        onClick={props.closeResources}
                                    >
                                        Finish
                                    </button>
                                </div>
                            </div> */}
                        </React.Fragment>
                    )}

                </div>
            )}
            <DialogBox
                itsclass={"add-dialog"}
                heading={"Error"}
                message={props.alertMessage}
                show={props.showAlert}
                closedialog={props.closeAlert}
            />

            <DialogBox
                itsclass={"add-dialog"}
                heading={"Success"}
                message={props.displayText}
                show={props.currentForm === "success"}
                closedialog={props.closeDialog}
            />

            <WaitingDialog
                itsclass={"add-dialog"}
                heading={"Processing..."}
                message={"Please wait..."}
                show={props.currentForm === "processing"}
            />
        </>
    )
}

export { ProfileCreationPage }
