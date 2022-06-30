import { useState } from "react";
import { Appheader } from '../header/header-component';
import { Instruction } from '../utilities/utility-components'
import { DialogBox, WaitingDialog,DialogBoxTwoOption } from "../dialog/dialog-component";
import './byod-join-component.css';

function GlowSVG(props) {
    if (!props.button_pressed) {
        return (<></>)
    }
    return (
        <svg>
        <circle className="svgpulse" x="0" y="0" r="33.5" fill-opacity="0" stroke={props.GLOW_COLOR}/>
        </svg>
    )
}

function PodOverview(props) {
    if (!props.connected && !props.authenticated) {
        return (<>
        </>)
    }
    const margin = { marginTop: "13px" };
    const margin2 = { marginTop: "22px" };

    return (
        <div className="list-container">
            <div className="pod-overview-button" onClick={props.requestHelp}>
                <svg width="80px" height="80px" style={margin2} viewBox="-40 -40 80 80">
                    <svg x="-8.5" y="-13.5" width="17" height="27" viewBox="0 0 17 27">
                        <use xlinkHref={"../assets/img/mic.svg#5"} fill={props.POD_COLOR}></use>
                    </svg>
                    <GlowSVG button_pressed={props.button_pressed} GLOW_COLOR={props.GLOW_COLOR} />
                    <svg>
                        <circle x="0" y="0" r="30.5" fill-opacity="0" stroke-width="3" stroke={props.POD_COLOR}/>
                        </svg>
                </svg>
                <div style={margin}>Help</div>
            </div>
        </div>
    )
}

function LandingPage(props) {
    const [pcode, setPcode] = useState("");
    if (props.connected) {
        return (
            <></>
        )
    }

    const changeTouppercase = () => {
        const val = document.getElementById("passcode").value.trim();
        setPcode(val.toUpperCase())
    }
    const verify = () => {
        const passcode = document.getElementById("passcode").value.trim();
        const name = document.getElementById("name").value.trim();
        props.verifyInputAndAudio(name, passcode);
    }

    return (
        <div className="container">
            <Instruction instructions="Please type your name and passcode to join a discussion." />
            <Instruction instructions="If rejoining a discussion, type the same name you used previously." />
            <input className="text-input" name="name" id="name" placeholder="Name" />
            <input className="text-input" id="passcode" value={pcode} placeholder="Passcode (4 characters)" maxLength="4" onInput={changeTouppercase} />
            <button className="medium-button basic-button" onClick={verify}>Join Discussion</button>
        </div>
    )
}




function DialogBoxes(props) {
    if (!props.globalshow) {
        return (<></>)
    }

    return (
        <>
            <DialogBoxTwoOption
                show={props.specificshow === 'NavGuard'}
                heading = {"Stop Recording"}
                body = {"Leaving this page will stop recording. Are you sure you want to continue?"}
                deletebuttonaction={props.navigateToLogin}
                cancelbuttonaction = {props.closeDialog}
            />

            <DialogBox
                itsclass={"add-dialog"}
                heading={'Failed to Join'}
                message={props.displayText}
                show={props.specificshow === 'JoinError'}
                closedialog={props.closeDialog} />

            <DialogBox
                itsclass={"add-dialog"}
                heading={'Discussion Closed'}
                message={props.displayText}
                show={props.specificshow === 'ClosedSession'}
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

function ByodJoinPage(props) {

    const backClick = () => {
        return props.navigate('/')
    }
    return (
        <div className="container">
            <Appheader 
                title={props.pageTitle}
                leftText = {false}
                rightText = {""}
                rightEnabled = {false}
                nav={backClick} />
            <LandingPage
                connected={props.connected}
                verifyInputAndAudio={props.verifyInputAndAudio}

            />
            <PodOverview
                connected={props.connected}
                authenticated={props.authenticated}
                GLOW_COLOR={props.GLOW_COLOR}
                POD_COLOR={props.POD_COLOR}
                button_pressed={props.button_pressed}
                requestHelp = {props.requestHelp}
            />
            <DialogBoxes
                globalshow={props.currentForm !== ""}
                specificshow={props.currentForm}
                closeDialog={props.closeDialog}
                displayText={props.displayText}
                navigateToLogin = {props.navigateToLogin}
            />
        </div>
    )
}

export { ByodJoinPage }