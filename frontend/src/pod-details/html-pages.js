import { GenericDialogBox } from '../dialog/dialog-component'
import { AppSectionBoxComponent } from '../section-box/section-box-component'
import { AppTimelineSlider } from '../components/timeline-slider/timeline-slider-component'
import { AppTimeline } from '../timeline/timeline-component'
import { AppHeatMapComponent } from '../heat-map/heat-map-component'
import { AppFeaturesComponent } from '../features/features-component'
import { AppRadarComponent } from '../radar/radar-component'
import { AppSpinner } from '../spinner/spinner-component'
import { AppSessionToolbar } from '../session-toolbar/session-toolbar-component'
import { AppKeywordsComponent } from '../keywords/keywords-component'
import { Appheader } from '../header/header-component'
import style from './pod.module.css'
import React from 'react'
import {isMobile} from 'react-device-detect'

function PodComponentPages(props) {
    return (
        <>
            <div className={style.container}>
                <Appheader
                    title={props.sessionDevice.name}
                    leftText={false}
                    rightText={"Option"}
                    rightEnabled={true}
                    rightTextClick={() => props.openDialog("Options")}
                    nav={props.navigateToSession}
                />

                <div className={style[isMobile ? "overview-container-mobile" : "overview-container-desktop"]}>
                    <br />
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
                            session={props.session}
                            sessionDevice={props.sessionDevice}
                            transcripts={props.displayTranscripts}
                            start={props.startTime}
                            end={props.endTime}
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
                <div className={style.footer}>
                    {props.session ? <AppSessionToolbar session={props.session} closingSession={props.onSessionClosing} /> : <></>}
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
                {props.currentForm === "Transcript" ?
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>Transcript</div>
                        <div className={style["dialog-body"]}>{props.currentTranscript.transcript}</div>
                        <div className={style["dialog-button-container"]}>
                             <button className={`${style["dialog-button"]} ${style["right-button"]}`} onClick={props.closeDialog}>Close</button>
                            <button className={`${style["dialog-button"]} ${style["left-button"]}`} onClick={props.seeAllTranscripts}>View All</button>
                        </div>
                    </div>
                    :
                    <></>
                }

                {props.currentForm == "Options" ?
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>Device Options</div>
                        <button className={style["basic-button"]} onClick={() => props.openDialog("RemoveDevice")}>Disconnect Device</button>
                        <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
                    </div>
                    :
                    <></>
                }

                {props.currentForm == "RemoveDevice" ?
                    <div className={style["dialog-content"]}>
                        <div className={style["dialog-heading"]}>Disconnect Device</div>
                        {!props.deleteDeviceToggle ?
                            <React.Fragment>
                                <div className={style["dialog-body"]}>Are you sure you want to remove this device?</div>
                                <div className={style["dialog-body"]}>All data will be saved, but the device will be disconnected from the discussion.</div>
                            </React.Fragment>
                            :
                            <></>
                        }

                        {props.deleteDeviceToggle ?
                            <React.Fragment>
                                <div className={style["dialog-body"]}>Are you sure you want to delete this device?</div>
                                <div className={style["dialog-body"]}>All data for this device will be lost and the device will be disconnected.</div>
                            </React.Fragment>
                            :
                            <></>
                        }
                        <label className={style["dc-checkbox"]}>Delete device
                            <input id='cbxDelete' type="checkbox" onKeyUp={() => props.setDeleteDeviceToggle(document.getElementById('cbxDelete').value)} />
                            <span className={style["checkmark"]}></span>
                        </label>
                        <div className={style["dialog-button-container"]}>
                            <button className={style["basic-button"]} onClick={() => props.removeDeviceFromSession(props.deleteDeviceToggle)}>Confirm</button>
                            <button className={style["cancel-button"]} onClick={props.closeDialog}>Cancel</button>
                        </div>
                    </div>
                    :
                    <></>
                }
            </GenericDialogBox>
        </>
    )
}
export { PodComponentPages }
