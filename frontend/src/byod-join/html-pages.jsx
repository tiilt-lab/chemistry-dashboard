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
import SessionQRCode from "../feedback-form/session-qrcode";

import style from "./byod-join.module.css"
import style2 from "../pod-details/pod.module.css"
import style3 from "../manage-keyword-lists/manage-keyword-lists.module.css"
import style4 from "../components/context-menu/context-menu.module.css"
import style5 from "../sessions/sessions.module.css"
import MicIcon from "@icons/Mic"
import Checkmark from "@assets/img/checkmark.svg"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { AppInfographicsComparison } from "../components/infographics-view/infographics-comparison"

function ByodJoinPage(props) {
    // console.log(props, 'props')
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
                            rightText={"Option"}
                            rightEnabled={
                                props.joinwith === "Video" ||
                                props.joinwith === "Videocartoonify"
                                    ? true
                                    : false
                            }
                            rightTextClick={() =>
                                props.joinwith === "Video" ||
                                props.joinwith === "Videocartoonify"
                                    ? props.openDialog("Options")
                                    : props.openDialog("")
                            }
                            nav={() => props.navigateToLogin()}
                        />
                        {!props.connected && (
                            <React.Fragment>
                                <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                    <div>
                                        <div className="my-1.5 font-sans text-base leading-5 font-normal text-[#727278]">
                                            Please type your name and passcode
                                            to join a discussion.
                                        </div>
                                        <div className="my-1.5 font-sans text-xs leading-5 font-normal text-[#727278]">
                                            If rejoining a discussion, type the
                                            same name you used previously.
                                        </div>
                                    </div>
                                    <div>
                                        <div>Device Name:</div>
                                        <input
                                            className="text-box small-section"
                                            id="name"
                                            placeholder="Name"
                                        />
                                        <div>Numbers of Collaborators:</div>
                                        <select
                                            id="collaborators"
                                            className="dropdown small-section"
                                        >
                                            <option value="0">
                                                0(Automatic)
                                            </option>
                                            <option value="1">1</option>
                                            <option value="2">2</option>
                                            <option value="3">3</option>
                                            <option value="4">4</option>
                                            <option value="5">5</option>
                                            <option value="6">6</option>
                                            <option value="7">7</option>
                                            <option value="8">8</option>
                                        </select>
                                        <div>Passcode:</div>
                                        <input
                                            className="text-box small-section"
                                            id="passcode"
                                            value={props.pcode}
                                            placeholder="Passcode (4 characters)"
                                            onInput={(event) =>
                                                props.changeTouppercase(event)
                                            }
                                        />
                                        {props.wrongInput
                                            ? "Your password must be 4 characters long."
                                            : ""}
                                        <div>Join With:</div>
                                        <select
                                            id="joinwith"
                                            className="dropdown small-section"
                                        >
                                            <option value="Audio">Audio</option>
                                            {/*<option value="Video">Video</option>
                    <option value="Videocartoonify">Video(Cartoon)</option>*/}
                                        </select>
                                    </div>
                                    <button
                                        className="wide-button"
                                        onClick={() =>
                                            props.verifyInputAndAudio(
                                                document
                                                    .getElementById("name")
                                                    .value.trim(),
                                                document
                                                    .getElementById("passcode")
                                                    .value.trim(),
                                                document
                                                    .getElementById("joinwith")
                                                    .value.trim(),
                                                parseInt(
                                                    document
                                                        .getElementById(
                                                            "collaborators",
                                                        )
                                                        .value.trim(),
                                                ),
                                            )
                                        }
                                    >
                                        Connect to Server
                                    </button>
                                </div>
                            </React.Fragment>
                        )}
                        {props.connected &&
                            props.authenticated &&
                            !props.speakersValidated && (
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
                                        <div className="mt-2 h-fit w-[300px] sm:w-[400px] lg:w-3xl">
                                            {!props.speakers && (
                                                <div
                                                    className={
                                                        style3[
                                                            "load-text onload"
                                                        ]
                                                    }
                                                >
                                                    Loading...
                                                </div>
                                            )}
                                            {props.speakers &&
                                                props.speakers.length === 0 && (
                                                    <div
                                                        className={
                                                            style3[
                                                                "empty-keyword-list"
                                                            ]
                                                        }
                                                    >
                                                        <div
                                                            className={
                                                                style3[
                                                                    "load-text"
                                                                ]
                                                            }
                                                        >
                                                            {" "}
                                                            No Speakers{" "}
                                                        </div>
                                                        <div
                                                            className={
                                                                style3[
                                                                    "load-text-description"
                                                                ]
                                                            }
                                                        >
                                                            {" "}
                                                            Tap the button below
                                                            to add a speaker or
                                                            other button to join
                                                            automatically detect
                                                            speakers(less
                                                            accurate){" "}
                                                        </div>
                                                    </div>
                                                )}
                                            {props.speakers.map(
                                                (speaker, count) => (
                                                    <div
                                                        key={"speaker" + count}
                                                        className="my-3 flex flex-row items-center justify-between rounded-md border px-2 py-2"
                                                    >
                                                        {speaker.fingerprinted && (
                                                            <img
                                                                className="h-8 w-8"
                                                                alt="question"
                                                                src={Checkmark}
                                                            />
                                                        )}
                                                        <div
                                                            className={
                                                                style3[
                                                                    "click-mask"
                                                                ]
                                                            }
                                                            onClick={() => {}}
                                                        ></div>
                                                        <div className="flew-row flex grow text-center">
                                                            <div className="grow font-sans text-lg/loose font-bold text-[#58585C]">
                                                                {speaker.alias}
                                                            </div>
                                                        </div>
                                                        <AppContextMenu
                                                            className={
                                                                style3[
                                                                    "keyword-list-options"
                                                                ]
                                                            }
                                                        >
                                                            <div
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "fingerprintAudio",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Record
                                                                Fingerprint
                                                            </div>
                                                            <div
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "renameAlias",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Rename Alias
                                                            </div>
                                                        </AppContextMenu>
                                                    </div>
                                                ),
                                            )}
                                        </div>
                                        <div>
                                            <button
                                                className="wide-button"
                                                onClick={props.confirmSpeakers}
                                            >
                                                Join Discussion
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

            <GenericDialogBox
                show={
                    props.currentForm !== "" &&
                    props.currentForm !== "gottoselectedtranscript" &&
                    props.currentForm !== "gototranscript"
                }
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
                    (props.currentForm === "Options" && (
                        <div className={style2["dialog-content"]}>
                            <div className={style2["dialog-heading"]}>
                                Session Options
                            </div>
                            <button
                                className={style2["basic-button"]}
                                onClick={props.togglePreview}
                            >
                                {props.previewLabel}
                            </button>
                            <button
                                className={style2["cancel-button"]}
                                onClick={props.closeDialog}
                            >
                                Cancel
                            </button>
                        </div>
                    )) ||
                    (props.currentForm === "fingerprintAudio" && (
                        <div className="min-w-{300px} flex h-60 flex-col items-center justify-around text-center sm:h-70">
                            <div className="sans text-base/normal font-bold sm:text-xl/loose">
                                Record Speaker Fingerprint:
                            </div>
                            <VoiceRecorder
                                onAudioDownload={props.saveAudioFingerprint}
                                downloadable={false}
                                uploadAudioFile={false}
                                width="100%"
                                mainContainerStyle={{
                                    "margin-right": "auto",
                                    "margin-left": "auto",
                                }}
                                controllerContainerStyle={{ height: "3rem" }}
                            />
                            <button
                                className="toolbar-button z-40"
                                onClick={props.addSpeakerFingerprint}
                            >
                                Confirm
                            </button>
                            <button
                                className={style2["cancel-button"]}
                                onClick={props.closeDialog}
                            >
                                Cancel
                            </button>
                        </div>
                    )) ||
                    (props.currentForm === "renameAlias" && (
                        <div
                            className={style5["dialog-window"]}
                            style={{ "min-width": adjDim(270) + "px" }}
                        >
                            <div className={style5["dialog-heading"]}>
                                Update Alias Name:
                            </div>
                            <input
                                id="txtAlias"
                                defaultValue={props.selectedSpeaker.alias}
                                className={style5["field-input"]}
                                maxLength="64"
                            />
                            <div>
                                {props.invalidName
                                    ? "Your proposed rename is invalid."
                                    : ""}
                            </div>
                            <button
                                className={style5["basic-button"]}
                                onClick={() => {
                                    props.changeAliasName(
                                        document.getElementById("txtAlias")
                                            .value,
                                    )
                                }}
                            >
                                {" "}
                                Confirm
                            </button>
                            <button
                                className={style5["cancel-button"]}
                                onClick={props.closeDialog}
                            >
                                {" "}
                                Cancel
                            </button>
                        </div>
                    ))}
            </GenericDialogBox>

            <DialogBoxTwoOption
                show={props.currentForm === "NavGuard"}
                itsclass={style["dialog-window"]}
                heading={"Stop Recording"}
                body={
                    "Leaving this page will stop recording. Are you sure you want to continue?"
                }
                deletebuttonaction={() => props.navigateToLogin(true)}
                cancelbuttonaction={props.closeDialog}
            />

            <DialogBox
                itsclass={"add-dialog"}
                heading={"Failed to Join"}
                message={props.displayText}
                show={props.currentForm === "JoinError"}
                closedialog={props.closeDialog}
            />

            <DialogBox
                itsclass={"add-dialog"}
                heading={"Missing Speaker Fingerprints"}
                message={props.displayText}
                show={props.currentForm === "FingerprintingError"}
                closedialog={props.closeDialog}
            />

            <GenericDialogBox
                itsclass={"add-dialog small-section"}
                heading={"Discussion Closed"}
                show={props.currentForm === "ClosedSession"}
            >
                <div className="text-xl/loose font-sans font-bold m-2">Discussion Closed</div>
                <div className="text-base font-sans font-normal m-2">{props.displayText}</div>
                <SessionQRCode sessionId={props.prevSessionId} />
                <button className="option-button font-sans small-section bg-red-500 hover:bg-red-400 m-2" onClick={props.closeDialog}>Close</button>
            </GenericDialogBox>

            <WaitingDialog
                itsclass={"add-dialog"}
                heading={"Connecting..."}
                message={"Please wait..."}
                show={props.currentForm === "Connecting"}
            />

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

export { ByodJoinPage }
