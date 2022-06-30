import React from 'react'
import style from './pods-overview.module.css'
import style2 from '../dialog/dialog.module.css'
import {Appheader} from '../header/header-component'
import { GenericDialogBox } from '../dialog/dialog-component'
import {AppSessionToolbar} from '../session-toolbar/session-toolbar-component'

import micIcon from '../assets/img/mic.svg'
import iconPod from '../assets/img/icon-pod.svg'
import downloadIcon from  '../assets/img/download.svg'
import iconGraph from '../assets/img/icon-graph.svg'


function PodsOverviewPages(props){
    return(
        <>
        <div className={style.container}>
            <Appheader 
                title={"Overview"}
                leftText={false}
                rightText={props.getPasscode()}
                rightEnabled={props.session.recording}
                rightTextClick={()=>{props.openDialog("Passcode")}}
                nav={props.navigateToSessions} 
            />
            <div className={style["list-container"]}>
                {(props.sessionDevices === undefined) ? <div className={style["load-text"]} >Loading...</div> : <></>}
                {(props.sessionDevices !== undefined && Object.keys(props.sessionDevices).length === 0) ? <div className={style["load-text"]} > No pods specified</div> : <></>}
                {
                    props.sessionDevices.map((device,index)=>(
                        <div key={index} onClick={()=> props.goToDevice(device)} className={style["pod-overview-button"]}>
                            <svg className={style["pod-overview-icon"]} width="80px" height="80px" viewBox="-40 -40 80 80">                                                                                                                                                                           
                                <svg x="-8.5" y="-13.5" width="17" height="27" viewBox="0 0 17 27">
                                    <use xlinkHref={`${micIcon}#5`}  fill={device.connected ? props.POD_ON_COLOR : props.POD_OFF_COLOR}></use>
                                </svg>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
                                {device.button_pressed ? <svg><circle className={style.svgpulse} x="0" y="0" r="33.5" fill-opacity="0" stroke={props.GLOW_COLOR}></circle> </svg> : <></> }
                                <svg><circle x="0" y="0" r="30.5" fill-opacity="0" stroke-width="3" stroke={device.connected ? props.POD_ON_COLOR : props.POD_OFF_COLOR }></circle></svg>
                            </svg>
                            <div>{device.name}</div>
                        </div>
                    ))
                  }
            </div>
            <div className={style.footer}>
                {props.session!== null  ?
                 <AppSessionToolbar  session={props.session} onSessionClosing={props.onSessionClosing}>
                    
                    {!props.session.end_date ?
                    <span className={style["toolbar-button"]} onClick={()=> props.openDialog("AddDevice")} >
                        <img alt='icon-pod' className={style["button-icon"]} src={iconPod} />
                        <div className={style["button-text"]}>Add Pod</div>
                    </span>
                    :
                    <></>}
                    <span className={style["toolbar-button"]} onClick={props.exportSession} >
                        <img  alt='download' className={style["button-icon"]} src={downloadIcon} />
                        <div className={style["button-text"]}>Download</div>
                    </span>
                    <span className={style["toolbar-button"]} onClick={props.goToGraph}>
                            <img alt='graph' className={style["button-icon"]} src={iconGraph} />
                            <div className={style["button-text"]}>Graph</div>
                    </span>
                </AppSessionToolbar> 
                :
                <></>
                }
        </div>
</div>

<GenericDialogBox show={props.currentForm !== ""} >
    { props.currentForm == "AddDevice" ?
        <div>
            <div className={style2["dialog-heading"]}>Add pod to Session</div>
            { props.devices.length > 0 ?
            <React.Fragment>
                <select id='ddDevice' className={style["dropdown-input"]}>
                    {
                       props.devices.map((device, index)=>(
                        <option key={index} defaultValue={device.id}>{device.name}</option>
                       )) 
                    }
                </select>
                <button className={style["basic-button"]} onClick={()=> props.addPodToSession(document.getElementById('ddDevice').value)}>Add</button>
            </React.Fragment>
            :
            <></>}
            {props.devices.length == 0 ? <div className={style["unavailable-text"]}>No devices available.</div> : <></> }
            <button className={style["cancel-button"]} onClick={props.closeDialog}>Close</button>
        </div>
    :
        <></>
    }
    { props.currentForm === "Passcode" ?
    <div>
        <div className={style2["dialog-heading"]}>Passcode Settings</div>
        <button className={style["basic-button"]} onClick={()=> props.setPasscodeState('lock')}>Lock</button>
        <button className={style["basic-button"]} onClick={()=> props.setPasscodeState('unlock')}>Unlock</button>
        <button className={style["basic-button"]} onClick= {()=> props.setPasscodeState('refresh')}>Refresh</button>
        <button className={style["cancel-button"]}  onClick={props.closeDialog}>Cancel</button>
    </div>
    :
    <></>}
</GenericDialogBox>
        </>
    )
}

export {PodsOverviewPages}
