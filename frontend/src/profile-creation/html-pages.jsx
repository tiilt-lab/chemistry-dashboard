import React, { useState } from "react"
import { Appheader } from "../header/header-component"
import { ReactMediaRecorder } from "react-media-recorder";
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
                            <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                <div className="w-[300px] px-2 sm:w-[400px] lg:w-3xl">
                                    <div className="my-1.5 font-sans text-base/loose font-medium text-[#727278]">
                                        Please add a Speaker Fingerprint
                                        for each speaker
                                    </div>
                                    <div className="my-1.5 font-sans text-xs/normal font-normal text-[#727278]">
                                        Each speaker must record and
                                        temporarily save a short 3-5
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

                                            <video id="video_playback" controls width={500} height={500} />
                                            <button className="toolbar-button z-40" onClick={props.startRecording} >Record Again</button>
                                            <button className="toolbar-button z-40" onClick={props.saveRecording} >Save Recording</button>
                                        </div>
                                        :
                                        <div>

                                            <video id="video_preview" controls autoPlay loop width={500} height={500} />
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
                            </div>
                        </React.Fragment>
                    )}
                    {props.connected &&
                        props.authenticated &&
                        props.speakersValidated && (
                            <>
                                <div className="toolbar-view-container">
                                    {props.session ? (
                                        <AppSessionToolbar
                                            session={props.session}
                                            closingSession={
                                                props.disconnect
                                            }
                                            fromClient={true}
                                            menus={[
                                                {
                                                    title: "Group",
                                                    action: () =>
                                                        props.viewGroup(),
                                                },
                                                {
                                                    title: "Individual",
                                                    action: () =>
                                                        props.viewIndividual(),
                                                },
                                                {
                                                    title: "Comparison",
                                                    action: () =>
                                                        props.viewComparison(),
                                                },
                                            ]}
                                        />
                                    ) : (
                                        <></>
                                    )}
                                    <div className="center-column-container">
                                        <br />
                                        {props.joinwith === "Audio" && (
                                            <AppSectionBoxComponent
                                                heading={"Audio control:"}
                                            >
                                                <div
                                                    className={
                                                        style[
                                                        "pod-overview-button"
                                                        ]
                                                    }
                                                    style={{
                                                        margin: "0 auto",
                                                    }}
                                                    onClick={
                                                        props.requestHelp
                                                    }
                                                >
                                                    <svg
                                                        width="80px"
                                                        height="80px"
                                                        style={{
                                                            marginTop:
                                                                "22px",
                                                        }}
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
                                                                    props.POD_COLOR
                                                                }
                                                            ></MicIcon>
                                                        </svg>
                                                        {props.button_pressed ? (
                                                            <svg>
                                                                <circle
                                                                    className={
                                                                        style.svgpulse
                                                                    }
                                                                    x="0"
                                                                    y="0"
                                                                    r="33.5"
                                                                    fill-opacity="0"
                                                                    stroke={
                                                                        props.GLOW_COLOR
                                                                    }
                                                                />
                                                            </svg>
                                                        ) : (
                                                            <></>
                                                        )}
                                                        <svg>
                                                            <circle
                                                                x="0"
                                                                y="0"
                                                                r="30.5"
                                                                fill-opacity="0"
                                                                stroke-width="3"
                                                                stroke={
                                                                    props.POD_COLOR
                                                                }
                                                            />
                                                        </svg>
                                                    </svg>
                                                    <div
                                                        style={{
                                                            marginTop:
                                                                "13px",
                                                        }}
                                                    >
                                                        Help
                                                    </div>
                                                </div>
                                            </AppSectionBoxComponent>
                                        )}

                                        {props.joinwith === "Video" && (
                                            <AppSectionBoxComponent
                                                heading={"Video control:"}
                                            >
                                                <div
                                                    className={
                                                        style[
                                                        "video-container"
                                                        ]
                                                    }
                                                    style={{
                                                        display:
                                                            props.preview
                                                                ? "block"
                                                                : "none",
                                                    }}
                                                >
                                                    <video
                                                        controls={true}
                                                        muted={true}
                                                        autoPlay={true}
                                                        playsInline={true}
                                                        style={{
                                                            marginLeft:
                                                                "20px",
                                                        }}
                                                    />
                                                </div>
                                            </AppSectionBoxComponent>
                                        )}

                                        {props.joinwith ===
                                            "Videocartoonify" && (
                                                <AppSectionBoxComponent
                                                    heading={"Video control:"}
                                                >
                                                    <div
                                                        className={
                                                            style[
                                                            "video-container"
                                                            ]
                                                        }
                                                        style={{
                                                            display:
                                                                props.preview
                                                                    ? "block"
                                                                    : "none",
                                                        }}
                                                    >
                                                        <video
                                                            controls={true}
                                                            muted={true}
                                                            style={{
                                                                marginLeft:
                                                                    "20px",
                                                            }}
                                                        />
                                                        <img
                                                            style={{
                                                                marginLeft:
                                                                    "12px",
                                                            }}
                                                            width="150"
                                                            height="80"
                                                            src={
                                                                props.cartoonImgUrl
                                                            }
                                                        />
                                                    </div>
                                                </AppSectionBoxComponent>
                                            )}
                                        <AppInfographicsComparison
                                            displayTranscripts={
                                                props.displayTranscripts
                                            }
                                            fromclient={true}
                                            onClickedTimeline={
                                                props.onClickedTimeline
                                            }
                                            radarTrigger={
                                                props.radarTrigger
                                            }
                                            session={props.session}
                                            sessionDevice={
                                                props.sessionDevice
                                            }
                                            setRange={props.setRange}
                                            showBoxes={props.showBoxes}
                                            showFeatures={
                                                props.showFeatures
                                            }
                                            startTime={props.startTime}
                                            endTime={props.endTime}
                                            speakers={props.speakers}
                                            selectedSpkrId1={
                                                props.selectedSpkrId1
                                            }
                                            setSelectedSpkrId1={
                                                props.setSelectedSpkrId1
                                            }
                                            selectedSpkrId2={
                                                props.selectedSpkrId2
                                            }
                                            setSelectedSpkrId2={
                                                props.setSelectedSpkrId2
                                            }
                                            spkr1Transcripts={
                                                props.spkr1Transcripts
                                            }
                                            spkr2Transcripts={
                                                props.spkr2Transcripts
                                            }
                                            details={props.details}
                                        />
                                    </div>
                                    {props.loading() ? (
                                        <AppSpinner></AppSpinner>
                                    ) : (
                                        <></>
                                    )}
                                </div>
                            </>
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
        </>
    )
}

export { ProfileCreationPage }
