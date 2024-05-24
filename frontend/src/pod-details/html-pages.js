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
import { isLargeScreen } from '../myhooks/custom-hooks';
import style from './pod.module.css'
import React from 'react'
import ReactMultiSelectCheckboxes from "react-multiselect-checkboxes";

function PodComponentPages(props) {
    
    return (
        <>
            <div className={style.container}>
                <Appheader
                    title={props.sessionDevice.name}
                    leftText={false}
                    rightText={"Option"}
                    rightEnabled={props.hideDetails ? false : true}
                    rightTextClick={() => props.openDialog("Options")}
                    nav={props.navigateToSession}
                />
                
                {props.hideDetails ? 
                <div className={isLargeScreen() ? style["overview-container-large"] : style["overview-container-small"]}>
                <br />
                <AppSectionBoxComponent heading={"Box 1:"} >
                </AppSectionBoxComponent>
                
                <AppSectionBoxComponent heading={"Box 2:"} >
                </AppSectionBoxComponent>
                
                <AppSectionBoxComponent heading={"Box 3:"} >
                </AppSectionBoxComponent>
                
                <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={props.toggleDetails}>Show Details</button >
                
                </div>
                :
                <div className={isLargeScreen() ? style["overview-container-large"] : style["overview-container-small"]}>
                    <br />
                    {((props.showBoxes.length > 0) && props.showBoxes[0]['clicked']) ?
                    <AppSectionBoxComponent heading={"Timeline control:"} >
                        <AppTimelineSlider id='timeSlider' inputChanged={props.setRange} />
                    </AppSectionBoxComponent>
                    : <></>
                    }
                    
                    {((props.showBoxes.length > 0) && props.showBoxes[1]['clicked']) ?
                    <AppSectionBoxComponent heading={"Discussion timeline:"}>
                        <AppTimeline
                            clickedTimeline={props.onClickedTimeline}
                            session={props.session}
                            transcripts={props.displayTranscripts}
                            start={props.startTime}
                            end={props.endTime}
                        />
                    </AppSectionBoxComponent>
                    : <></>
                    }
                    
                    {((props.showBoxes.length > 0) && props.showBoxes[2]['clicked']) ?
                    <AppSectionBoxComponent heading={"Keyword detection:"}>
                        <AppKeywordsComponent
                            session={props.session}
                            sessionDevice={props.sessionDevice}
                            transcripts={props.displayTranscripts}
                            start={props.startTime}
                            end={props.endTime}
                        />
                    </AppSectionBoxComponent>
                    : <></>
                    }

                    {((props.showBoxes.length > 0) && props.showBoxes[3]['clicked']) ?
                    <AppSectionBoxComponent heading={"Discussion features:"}>
                        <AppFeaturesComponent 
                        session={props.session} 
                        transcripts={props.displayTranscripts}
                        showFeatures={props.showFeatures} />
                    </AppSectionBoxComponent>
                    : <></>
                    }
                    
                    {((props.showBoxes.length > 0) && props.showBoxes[4]['clicked']) ?
                    <AppSectionBoxComponent heading={"Radar chart:"}>
                        <AppRadarComponent 
                        session={props.session} 
                        transcripts={props.displayTranscripts}
                        radarTrigger={props.radarTrigger}
                        start={props.startTime}
                        end={props.endTime}
                        showFeatures={props.showFeatures} />
                    </AppSectionBoxComponent>
                    : <></>
                    }
                    
                    <button className={isLargeScreen() ? `${style["basic-button"]} ${style["medium-button"]}` : `${style["basic-button"]} ${style["small-button"]}`} onClick={props.toggleDetails}>Hide Details</button >
                </div>
                }
                {props.loading() ? <AppSpinner></AppSpinner> : <></>}
                <div className={style.footer}>
                    {props.session ? <AppSessionToolbar session={props.session} closingSession={props.onSessionClosing} /> : <></>}
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""} optionsCase={props.currentForm == "Options"}>
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
                        <div className={style["dialog-heading"]}>Section Boxes</div>
                        <div className={style["dialog-dropdown"]}>   
                          <ReactMultiSelectCheckboxes 
                          options={props.showBoxes} 
                          value={props.showBoxes.filter((feature) => feature['clicked'])} 
                          onChange={props.handleCheckBoxes}/>
                        </div>
                        <div className={style["dialog-heading"]}>Discussion Features</div>
                        <div className={style["dialog-dropdown"]}>   
                          <ReactMultiSelectCheckboxes 
                          options={props.showFeatures} 
                          value={props.showFeatures.filter((feature) => feature['clicked'])} 
                          onChange={props.handleCheckFeats}/>
                        </div>
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
                            <input id='cbxDelete' type="checkbox" checked={props.deleteDeviceToggle} value={props.deleteDeviceToggle} onChange={() => props.setDeleteDeviceToggle(!props.deleteDeviceToggle)} />
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
