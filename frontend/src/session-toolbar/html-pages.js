import style from './session-toolbar.module.css'
import style2 from '../dialog/dialog.module.css'
import {GenericDialogBox} from '../dialog/dialog-component'
import {AppSpinner} from '../spinner/spinner-component'
import React from 'react'
import { adjDim } from '../myhooks/custom-hooks'

function AppSessionPage(props){

    return(
        <>
        <div className={props.sessionEnding ? `${style["footer-bar"]} ${style["dialog-blur"]}`: style["footer-bar"]} >
            <div className={style["session-toolbar"]} style={{"grid-template-columns": adjDim(120) + "px auto " + adjDim(120) + "px",}}>
                <span className={style["session-time"]}>
                    <div className={style.time}>{props.timeText}</div>
                    <div className={style.info}>Total duration</div>
                </span>
                <span className={style["middle-content"]}>
                    <React.Fragment>
                        {props.innerhtml}
                    </React.Fragment>
                </span>
                {props.session.recording ?
                <span  className={style["session-end"]} onClick={props.onEndSession}>
                    <button className={style["end-button"]}>End</button>
                </span>
                :
                <></>}
            </div>
        </div>

<GenericDialogBox show={props.sessionEnding} >
    <div className={style["dialog-content"]}>
        <div className={style2["dialog-heading"]}>Session Ending...</div>
        <div className={style["dialog-spinner"]}><AppSpinner></AppSpinner></div>
    </div>
</GenericDialogBox>
        </>
    )
}

export {AppSessionPage}
