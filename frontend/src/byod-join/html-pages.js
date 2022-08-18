import React, { useState } from "react";
import { Appheader } from '../header/header-component';
import { DialogBox, WaitingDialog, DialogBoxTwoOption } from "../dialog/dialog-component";
import style from './byod-join.module.css';
import micIcon from '../assets/img/mic.svg'


function ByodJoinPage(props) {
    console.log(props, 'props')
    return (
        <>
            <div className={style.container}>
                <Appheader
                    title={props.pageTitle}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={() => props.navigate('/')} />
                {!props.connected ?
                    <React.Fragment>
                        <div className={style.instruction}>Please type your name and passcode to join a discussion.</div>
                        <div className={style.instruction}>If rejoining a discussion, type the same name you used previously.</div>
                        <input className={style["text-input"]} name="name" id="name" value={props.name} placeholder="Name" />
                        <input className={style["text-input"]} id="passcode" value={props.pcode} placeholder="Passcode (4 characters)" maxLength="4" onInput={(event) => props.changeTouppercase(event)} />
                        <select id="joinwith" className={style["dropdown-input"]}>
                            <option value="Audio">Audio</option>
                            <option value="Video">Video</option>
                        </select>
                        <button className={`${style["basic-button"]} ${style["medium-button"]}`} onClick={() => props.verifyInputAndAudio(document.getElementById("name").value.trim(), document.getElementById("passcode").value.trim(), document.getElementById("joinwith").value.trim())}>Join Discussion</button>
                    </React.Fragment>
                    :
                    <></>
                }
                {
                    (props.connected && props.authenticated) ?
                        <div className={style["list-container"]}>
                            <div className={style["pod-overview-button"]} onClick={props.requestHelp}>
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
                        </div>

                        :
                        <></>
                }
                {
                    (props.connected && props.joinwith === 'Video' && props.isStop === false) ?
                        <React.Fragment>
                            <div className={style["video-container"]}>
                                <video controls={true} muted={true}/>
                            </div>

                            {/* <button className={`${style["basic-button"]} ${style["medium-button"]}`} onClick={() => { props.mediaRecorder.start(1000); console.log(props.mediaRecorder.state); }}>Start Recording</button> */}
                            <button className={`${style["basic-button"]} ${style["medium-button"]}`} onClick={() => { props.mediaRecorder.stop(); console.log(props.mediaRecorder.state); }}>Stop Recording</button>
                        </React.Fragment>
                        :
                        <></>

                }

                {
                    (props.connected && props.joinwith === 'Video' && props.isStop === true) ?
                        <div className={style["video-container"]}>
                            <video id='video-player' controls >
                                <source src={props.recordedvideo} type="video/mp4" />
                            </video>
                        </div>
                        :
                        <></>

                }
            </div>

            <DialogBoxTwoOption
                show={props.currentForm === 'NavGuard'}
                itsclass={style["dialog-window"]}
                heading={"Stop Recording"}
                body={"Leaving this page will stop recording. Are you sure you want to continue?"}
                deletebuttonaction={props.navigateToLogin}
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
                show={props.specificshow === 'Connecting'}
            />
        </>
    )
}

export { ByodJoinPage }