import React, { useState } from "react";
import { Appheader } from '../header/header-component';
import { DialogBox, WaitingDialog, DialogBoxTwoOption, GenericDialogBox } from "../dialog/dialog-component";
import { AppSectionBoxComponent } from '../section-box/section-box-component'
import { AppTimelineSlider } from '../components/timeline-slider/timeline-slider-component'
import { AppTimeline } from '../timeline/timeline-component'
import { AppHeatMapComponent } from '../heat-map/heat-map-component'
import { AppFeaturesComponent } from '../features/features-component'
import { AppRadarComponent } from '../radar/radar-component'
import { AppSpinner } from '../spinner/spinner-component'
import { AppSessionToolbar } from '../session-toolbar/session-toolbar-component'
import { AppKeywordsComponent } from '../keywords/keywords-component'
import { TranscriptsComponentClient } from '../transcripts/transcripts-component_client';
import { adjDim, isLargeScreen } from '../myhooks/custom-hooks';

import style from './byod-join.module.css';
import style2 from '../pod-details/pod.module.css'
import micIcon from '../assets/img/mic.svg'
import { AppContextMenu } from '../components/context-menu/context-menu-component'
import iconPod from "../assets/img/icon-pod.svg"
import lightIcon from "../assets/img/light.svg"

function ByodJoinPage(props) {
    // console.log(props, 'props')
    return (
        <>
        { (props.currentForm === "gottoselectedtranscript" && Object.keys(props.currentTranscript)) ?
            <TranscriptsComponentClient
                sessionDevice={props.sessionDevice}
                transcriptIndex={props.currentTranscript.id}
                setParentCurrentForm = {props.setCurrentForm}
            />
            :
            props.currentForm === "gototranscript" ?
            <TranscriptsComponentClient
                sessionDevice={props.sessionDevice}
                transcriptIndex={undefined}
                setParentCurrentForm = {props.setCurrentForm}
            />
            :
            <div className={style.container}>
                <Appheader
                    title={props.pageTitle}
                    leftText={false}
                    rightText={"Option"}
                    rightEnabled={(props.joinwith === 'Video' || props.joinwith === 'Videocartoonify')? true : false}
                    rightTextClick={() => (props.joinwith === 'Video' || props.joinwith === 'Videocartoonify')? props.openDialog("Options"): props.openDialog("")}
                    nav={() => props.navigateToLogin()} />
                {!props.connected ?
                    <React.Fragment>
                        <div className={style.instruction} style={{width: adjDim(343) + 'px',}}>Please type your name and passcode to join a discussion.</div>
                        <div className={style.instruction} style={{width: adjDim(343) + 'px',}}>If rejoining a discussion, type the same name you used previously.</div>
                        <input className={style["text-input"]}  style={{width: adjDim(330) + 'px',}} id="name" placeholder="Name" />
                        <input className={style["text-input"]}  style={{width: adjDim(330) + 'px',}} id="passcode" value={props.pcode} placeholder="Passcode (4 characters)" maxLength="4" onInput={(event) => props.changeTouppercase(event)} />
                        <select id="joinwith" className={style["dropdown-input"]}  style={{width: adjDim(350) + 'px',}}>
                            <option value="Audio">Audio</option>
                            <option value="Video">Video</option>
                            <option value="Videocartoonify">Video(Cartoon)</option>
                        </select>
                        <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} 
                        onClick={() => props.verifyInputAndAudio(document.getElementById("name").value.trim(), document.getElementById("passcode").value.trim(), document.getElementById("joinwith").value.trim())}>Join Discussion</button>
                    </React.Fragment>
                    :
                    <></>
                }
                {
                    (props.connected) ?
                        <>
                            <div className={style2["overview-container"]}>
                                <br />
                                {
                                    (props.authenticated && props.joinwith === 'Audio') ?
                                        <AppSectionBoxComponent heading={"Audio control:"} >
                                            <div className={style["pod-overview-button"]} style={{margin: '0 auto'}} onClick={props.requestHelp}>
                                                    <svg width="80px" height="80px" style={{ marginTop: "22px" }} viewBox="-40 -40 80 80">
                                                        <svg x="-8.5" y="-13.5" width="17" height="27" viewBox="0 0 17 27">
                                                            <use xlinkHref={`${micIcon}#5`} fill={props.POD_COLOR}></use>
                                                        </svg>
                                                        {props.button_pressed ?
                                                            <svg>
                                                                <circle className={style.svgpulse} x="0" y="0" r="33.5" fill-opacity="0" stroke={props.GLOW_COLOR} />
                                                            </svg>
                                                            :
                                                            <></>
                                                        }
                                                        <svg>
                                                            <circle x="0" y="0" r="30.5" fill-opacity="0" stroke-width="3" stroke={props.POD_COLOR} />
                                                        </svg>
                                                    </svg>
                                                    <div style={{ marginTop: "13px" }}>Help</div>
                                                </div>
                                        </AppSectionBoxComponent>
                                        :
                                        <></>
                                }

                                {
                                    (props.authenticated && props.joinwith === 'Video') ?
                                        <AppSectionBoxComponent heading={"Video control:"} >
                                            <div className={style["video-container"]} style={{display: props.preview ? 'block' : 'none' }}>
                                                <video controls={true} muted={true} style={{ marginLeft: "20px" }} />
                                               </div>
                                        </AppSectionBoxComponent>
                                        :
                                        <></>
                                }

{
                                    (props.authenticated && props.joinwith === 'Videocartoonify') ?
                                        <AppSectionBoxComponent heading={"Video control:"} >
                                            <div className={style["video-container"]} style={{display: props.preview ? 'block' : 'none' }}>
                                                <video controls={true} muted={true} style={{ marginLeft: "20px" }} />
                                                <img  style={{ marginLeft: "12px" }}  width="150" height="80" src={props.apiEndpoint+'api/v1/sessions/'+props.session.id+'/devices/'+props.sessionDevice.id+'/auth/'+props.authKey+'/streamimages'} />
                                            </div>
                                        </AppSectionBoxComponent>
                                        :
                                        <></>
                                }
                                <AppSectionBoxComponent heading={"Timeline control:"} >
                                    <AppTimelineSlider id='timeSlider' inputChanged={props.setRange} />
                                </AppSectionBoxComponent>

                                <AppSectionBoxComponent heading={"Discussion timeline:"}>
                                    <AppTimeline
                                        clickedTimeline={props.onClickedTimeline}
                                        session={props.session}
                                        transcripts={props.displayTranscripts}
                                        start={props.startTime}
                                        end={props.endTime}
                                    />
                                </AppSectionBoxComponent>

                                <AppSectionBoxComponent heading={"Keyword detection:"}>
                                    <AppKeywordsComponent
                                        clickedKeyword={props.onClickedKeyword}
                                        session={props.session}
                                        sessionDevice={props.sessionDevice}
                                        transcripts={props.displayTranscripts}
                                        start={props.startTime}
                                        end={props.endTime}
                                        fromclient={true}
                                    />
                                </AppSectionBoxComponent>

                                <AppSectionBoxComponent heading={"Discussion features:"}>
                                    <AppFeaturesComponent
                                        session={props.session}
                                        transcripts={props.displayTranscripts} />
                                </AppSectionBoxComponent>

                                <AppSectionBoxComponent heading={"Radar chart:"}>
                                    <AppRadarComponent
                                    session={props.session}
                                    transcripts={props.displayTranscripts}
                                    start={props.startTime}
                                    end={props.endTime} />
                                </AppSectionBoxComponent>
                            </div>
                            {props.loading() ? <AppSpinner></AppSpinner> : <></>}
                            <div className={style2.footer}>
                                {props.session ? <AppSessionToolbar session={props.session} closingSession={()=> props.disconnect(true)} /> : <></>}
                            </div>
                        </>

                        :
                        <></>
                }


            </div>
        }

            <GenericDialogBox show={props.currentForm !== "" && props.currentForm !== "gottoselectedtranscript" && props.currentForm !== "gototranscript" }>
                {props.currentForm === "Transcript" ?
                    <div className={style2["dialog-content"]}>
                        <div className={style2["dialog-heading"]}>Transcript</div>
                        <div className={style2["dialog-body"]}>{props.currentTranscript.transcript}</div>
                        <div className={style2["dialog-button-container"]}>
                             <button className={`${style2["dialog-button"]} ${style2["right-button"]}`} onClick={props.closeDialog}>Close</button>
                            <button className={`${style2["dialog-button"]} ${style2["left-button"]}`} onClick={props.seeAllTranscripts}>View All</button>
                        </div>
                    </div>
                    :
                    <></>
                }

                {(props.currentForm == "Options" ) ?
                    <div className={style2["dialog-content"]}>
                        <div className={style2["dialog-heading"]}>Session Options</div>
                        <button className={style2["basic-button"]} onClick={props.togglePreview}>{props.previewLabel}</button>
                        <button className={style2["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
                    </div>
                    :
                    <></>
                }


            </GenericDialogBox>

            <DialogBoxTwoOption
                show={props.currentForm === 'NavGuard'}
                itsclass={style["dialog-window"]}
                heading={"Stop Recording"}
                body={"Leaving this page will stop recording. Are you sure you want to continue?"}
                deletebuttonaction={()=>props.navigateToLogin(true)}
                cancelbuttonaction={props.closeDialog}
            />

            <DialogBox
                itsclass={"add-dialog"}
                heading={'Failed to Join'}
                message={props.displayText}
                show={props.currentForm === 'JoinError'}
                closedialog={props.closeDialog} />

            <DialogBox
                itsclass={"add-dialog"}
                heading={'Discussion Closed'}
                message={props.displayText}
                show={props.currentForm === 'ClosedSession'}
                closedialog={props.closeDialog} />

            <WaitingDialog
                itsclass={"add-dialog"}
                heading={'Connecting...'}
                message={'Please wait...'}
                show={props.currentForm === 'Connecting'}
            />
        </>
    )
}

export { ByodJoinPage }
