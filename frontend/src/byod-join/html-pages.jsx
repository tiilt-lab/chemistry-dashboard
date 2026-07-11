import React, { useState } from "react"
import { btnPrimary, btnPrimaryTall, btnSecondaryTall, dlgInput, dlgSelect, dlgPrimary, dlgError } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { PodMicRing } from "../components/pod-mic-ring"
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

import style from "./byod-join.module.css"
import style2 from "../pod-details/pod.module.css"
import style3 from "../manage-keyword-lists/manage-keyword-lists.module.css"
import style4 from "../components/context-menu/context-menu.module.css"
import style5 from "../sessions/sessions.module.css"
import MicIcon from "@icons/Mic"
import Check from "@icons/Check"
import Chevron from "@icons/Chevron"
import { MicChannelProbe } from "./mic-channel-probe"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { AppInfographicsComparison } from "../components/infographics-view/infographics-comparison"

const fieldLabel = "mb-1.5 block text-left text-sm font-semibold text-tiilt-ink"

function ByodJoinPage(props) {
    // Join-form niceties: prefer the prefilled code (link/QR) as a compact
    // chip; the Advanced disclosure starts open so the source/camera options
    // and mic check are visible without an extra tap.
    const [editCode, setEditCode] = useState(false)
    const [showAdvanced, setShowAdvanced] = useState(true)
    // Prefilled group name so joining takes zero typing when the exact name
    // doesn't matter. Random suffix keeps two groups in the same session from
    // colliding (a duplicate name would silently take over the other group's
    // device once it disconnects).
    const [defaultGroupName] = useState(
        () => "Group " + Math.floor(100 + Math.random() * 900),
    )
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
                            rightText={"Options"}
                            rightTextClick={() =>
                                props.joinwith === "Video" ||
                                    props.joinwith === "Videocartoonify"
                                    ? props.openDialog("Options")
                                    : props.openDialog("")
                            }
                            nav={() => props.navigateToLogin()}
                        />
                        {(!props.state.audioSocketOpen) && (
                            <div className={pageShell}>
                            <div className={formCard}>
                                <div className="mx-auto flex w-full max-w-md grow flex-col gap-4 overflow-y-auto px-4 py-6">
                                    <div className="text-sm leading-6 text-tiilt-muted">
                                        Type your name and passcode to join a
                                        session. If rejoining, use the same
                                        name as before.
                                    </div>
                                    <div>
                                        <label htmlFor="name" className={fieldLabel}>
                                            Group name
                                        </label>
                                        <input
                                            className={dlgInput}
                                            id="name"
                                            defaultValue={defaultGroupName}
                                            placeholder="e.g. Table 3"
                                        />
                                    </div>

                                    <div>
                                        <label htmlFor="passcode" className={fieldLabel}>
                                            Passcode
                                        </label>
                                        {props.pcode && !editCode ? (
                                            <div className="flex items-center justify-between rounded-xl border border-tiilt-line bg-tiilt-ground px-4 py-3">
                                                <span className="font-mono text-lg font-bold tracking-[0.2em] text-tiilt-ink">
                                                    {props.pcode}
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => setEditCode(true)}
                                                    className="cursor-pointer text-sm font-semibold text-tiilt transition hover:text-tiilt-deep"
                                                >
                                                    Change
                                                </button>
                                                <input
                                                    type="hidden"
                                                    id="passcode"
                                                    value={props.pcode}
                                                />
                                            </div>
                                        ) : (
                                            <input
                                                className={dlgInput}
                                                id="passcode"
                                                value={props.pcode}
                                                placeholder="Session word (e.g. MAPLE)"
                                                onInput={(event) =>
                                                    props.changeTouppercase(event)
                                                }
                                            />
                                        )}
                                        {props.wrongInput ? (
                                            <div className={dlgError + " mt-2"}>
                                                That passcode looks too
                                                long — it should be one
                                                short word.
                                            </div>
                                        ) : null}
                                    </div>
                                    <div>
                                        <button
                                            type="button"
                                            onClick={() => setShowAdvanced(!showAdvanced)}
                                            aria-expanded={showAdvanced}
                                            className="flex cursor-pointer items-center gap-1.5 text-sm font-semibold text-tiilt transition hover:text-tiilt-deep"
                                        >
                                            <Chevron
                                                direction={showAdvanced ? "down" : "right"}
                                                size={12}
                                            />
                                            Advanced options
                                        </button>
                                        <div className={showAdvanced ? "mt-3 flex flex-col gap-4" : "hidden"}>
                                            <div>
                                                <label htmlFor="joinwith" className={fieldLabel}>
                                                    Join with
                                                </label>
                                                <select
                                                    id="joinwith"
                                                    className={dlgSelect}
                                                >
                                                    <option value="Audio">Audio</option>
                                                    <option value="Video">Video</option>
                                                    <option value="Videocartoonify">Video (cartoon)</option>
                                                </select>
                                            </div>
                                            <div>
                                                <label htmlFor="collaborators" className={fieldLabel}>
                                                    Number of people in your group
                                                </label>
                                                <select
                                                    id="collaborators"
                                                    className={dlgSelect}
                                                >
                                                    <option value="0">
                                                        Detect automatically
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
                                            </div>
                                            <MicChannelProbe />
                                        </div>
                                    </div>
                                </div>
                                <div className="w-full flex-none border-t border-tiilt-line bg-white">
                                    <div className="mx-auto w-full max-w-md px-4 py-4">
                                        <button
                                            className={dlgPrimary + " w-full"}
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
                                            Connect to server
                                        </button>
                                    </div>
                                </div>
                            </div>
                            </div>
                        )}
                        {props.state.audioSocketOpen && props.joinwith === "Audio" &&
                            props.state.audioReady &&
                            !props.state.speakersValidated && (
                                <React.Fragment>
                                    <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                        <div className="w-[300px] px-2 sm:w-[400px] lg:w-3xl">
                                            <div className="my-1.5 font-sans text-base/loose font-medium text-tiilt-muted">
                                                Please add a Speaker Fingerprint
                                                for each speaker
                                            </div>
                                            <div className="my-1.5 font-sans text-xs/normal font-normal text-tiilt-muted">
                                                Each speaker must record and
                                                temporarily save a short 3-5
                                                second sample of their voice.
                                                This is used to track each
                                                speaker's metrics throughout a
                                                session and is deleted upon
                                                ending the session.
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
                                                            Tap Add speaker to
                                                            enroll each group
                                                            member, or Join
                                                            Session to detect
                                                            speakers
                                                            automatically (less
                                                            accurate).{" "}
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
                                                            <span
                                                                role="img"
                                                                aria-label="Fingerprinted"
                                                                className="text-tiilt-teal"
                                                            >
                                                                <Check size={32} />
                                                            </span>
                                                        )}
                                                        <div
                                                            className={
                                                                style3[
                                                                "click-mask"
                                                                ]
                                                            }
                                                            aria-hidden="true"
                                                        ></div>
                                                        <div className="flew-row flex grow text-center">
                                                            <div className="grow font-sans text-lg/loose font-bold text-tiilt-ink">
                                                                {speaker.alias}
                                                            </div>
                                                        </div>
                                                        <AppContextMenu
                                                            label={`Options for ${speaker.alias}`}
                                                            className={
                                                                style3[
                                                                "keyword-list-options"
                                                                ]
                                                            }
                                                        >
                                                            <button
                                                                role="menuitem"
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
                                                            </button>
                                                            <button
                                                                role="menuitem"
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "renameAlias",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Rename Alias
                                                            </button>

                                                            <button
                                                                role="menuitem"
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "savedAudioVideoFingerprint",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Saved Fingerprint
                                                            </button>
                                                        </AppContextMenu>
                                                    </div>
                                                ),
                                            )}
                                        </div>
                                        <div className="flex flex-col items-center">
                                            <button
                                                className={btnSecondaryTall + " m-0.5 w-60 @sm:m-3 @sm:w-80"}
                                                onClick={props.addSpeakerSlot}
                                            >
                                                + Add speaker
                                            </button>
                                            <button
                                                className={btnPrimaryTall + " m-0.5 w-60 @sm:m-3 @sm:w-80"}
                                                onClick={props.confirmSpeakers}
                                            >
                                                Join Session
                                            </button>
                                        </div>
                                    </div>
                                </React.Fragment>
                            )
                        }

                        {props.state.audioSocketOpen && props.state.videoSocketOpen && (props.joinwith === "Video" || props.joinwith === "Videocartoonify") &&
                            props.state.audioReady && props.state.videoReady &&
                            !props.state.speakersValidated && (
                                <React.Fragment>
                                    <div className="@container relative box-border flex grow flex-col items-center justify-between overflow-y-auto text-center">
                                        <div className="w-[300px] px-2 sm:w-[400px] lg:w-3xl">
                                            <div className="my-1.5 font-sans text-base/loose font-medium text-tiilt-muted">
                                                Please add a Speaker Fingerprint
                                                for each speaker
                                            </div>
                                            <div className="my-1.5 font-sans text-xs/normal font-normal text-tiilt-muted">
                                                Each speaker must record and
                                                temporarily save a short 3-5
                                                second sample of their voice.
                                                This is used to track each
                                                speaker's metrics throughout a
                                                session and is deleted upon
                                                ending the session.
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
                                                            Tap Add speaker to
                                                            enroll each group
                                                            member, or Join
                                                            Session to detect
                                                            speakers
                                                            automatically (less
                                                            accurate).{" "}
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
                                                            <span
                                                                role="img"
                                                                aria-label="Fingerprinted"
                                                                className="text-tiilt-teal"
                                                            >
                                                                <Check size={32} />
                                                            </span>
                                                        )}
                                                        <div
                                                            className={
                                                                style3[
                                                                "click-mask"
                                                                ]
                                                            }
                                                            aria-hidden="true"
                                                        ></div>
                                                        <div className="flew-row flex grow text-center">
                                                            <div className="grow font-sans text-lg/loose font-bold text-tiilt-ink">
                                                                {speaker.alias}
                                                            </div>
                                                        </div>
                                                        <AppContextMenu
                                                            label={`Options for ${speaker.alias}`}
                                                            className={
                                                                style3[
                                                                "keyword-list-options"
                                                                ]
                                                            }
                                                        >
                                                            <button
                                                                role="menuitem"
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
                                                            </button>
                                                            <button
                                                                role="menuitem"
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "renameAlias",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Rename Alias
                                                            </button>

                                                            <button
                                                                role="menuitem"
                                                                className={`${style4["menu-item"]} ${style4["black"]}`}
                                                                onClick={() => {
                                                                    props.openForms(
                                                                        "savedAudioVideoFingerprint",
                                                                        speaker,
                                                                    )
                                                                }}
                                                            >
                                                                Saved Fingerprint
                                                            </button>
                                                        </AppContextMenu>
                                                    </div>
                                                ),
                                            )}
                                        </div>
                                        <div className="flex flex-col items-center">
                                            <button
                                                className={btnSecondaryTall + " m-0.5 w-60 @sm:m-3 @sm:w-80"}
                                                onClick={props.addSpeakerSlot}
                                            >
                                                + Add speaker
                                            </button>
                                            <button
                                                className={btnPrimaryTall + " m-0.5 w-60 @sm:m-3 @sm:w-80"}
                                                onClick={props.confirmSpeakers}
                                            >
                                                Join Session
                                            </button>
                                        </div>
                                    </div>
                                </React.Fragment>
                            )
                        }

                        {props.state.audioSocketOpen &&
                            props.state.audioReady &&
                            props.state.speakersValidated && (
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
                                                        title: "Comparison",
                                                        action: () =>
                                                            props.viewComparison(),
                                                    },
                                                ]}
                                                participants={props.speakers.map((speaker, index) => (
                                                    {
                                                        alias: speaker.alias,
                                                        action: () => props.loadSpeakerMetrics(speaker.id, speaker.alias),
                                                    }
                                                ))}
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
                                                    <button
                                                        type="button"
                                                        aria-label="Request help"
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
                                                        <PodMicRing
                                                            style={{ marginTop: "22px" }}
                                                            color={props.POD_COLOR}
                                                            pulsing={!!props.button_pressed}
                                                            pulseClassName={style.svgpulse}
                                                        />
                                                        <div
                                                            style={{
                                                                marginTop:
                                                                    "13px",
                                                            }}
                                                        >
                                                            Help
                                                        </div>
                                                    </button>
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
                                                                alt="Your cartoon avatar preview"
                                                                src={
                                                                    props.cartoonImgUrl
                                                                }
                                                            />
                                                        </div>
                                                    </AppSectionBoxComponent>
                                                )}
                                            <AppInfographicsComparison
                                                displayTranscripts={props.displayTranscripts}
                                                displayVideoMetrics={props.displayVideoMetrics}
                                                fromclient={true}
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
                                                getSpeakerAliasFromID={props.getSpeakerAliasFromID}
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

            <GenericDialogBox onClose={props.closeDialog}
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
                                className={btnPrimary + " z-40"}
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
                            style={{ minWidth: "min(20rem, 76vw)" }}
                        >
                            <div className={style5["dialog-heading"]}>
                                Update Alias Name:
                            </div>
                            <input
                                aria-label="Alias name"
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
                    )) ||
                    (props.currentForm === "savedAudioVideoFingerprint" && (
                        <div
                            className={style5["dialog-window"]}
                            style={{ minWidth: "min(20rem, 76vw)" }}
                        >
                            <div className={style5["dialog-heading"]}>
                                Enter Username:
                            </div>
                            <input
                                aria-label="Username"
                                id="registeredusername"
                                className={style5["field-input"]}
                                maxLength="64"
                            />
                            <div className={props.savedFingerprintError ? dlgError : ""}>
                                {props.savedFingerprintError}
                            </div>
                            <button
                                className={style5["basic-button"]}
                                onClick={() => {
                                    props.startProcessingSavedSpeakerFingerprint(
                                        document.getElementById("registeredusername")
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
                    ))

                }
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

            {/* <GenericDialogBox
                itsclass={"add-dialog small-section"}
                heading={"Session Closed"}
                show={props.currentForm === "ClosedSession"}
            >
                <div className="text-xl/loose font-sans font-bold m-2">Session Closed</div>
                <div className="text-base font-sans font-normal m-2">{props.displayText}</div>
                <SessionQRCode sessionId={props.prevSessionId} />
                <button className="option-button font-sans small-section bg-red-500 hover:bg-red-400 m-2" onClick={props.closeDialog}>Close</button>
            </GenericDialogBox> */}

            <WaitingDialog
                itsclass={"add-dialog"}
                heading={"Connecting..."}
                message={"Please wait..."}
                show={props.currentForm === "Connecting"}
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

export { ByodJoinPage }
