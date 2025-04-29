import style from "./session-toolbar.module.css"
import style2 from "../dialog/dialog.module.css"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import React from "react"
import { isLargeScreen } from "../myhooks/custom-hooks"

function AppSessionPage(props) {
    return (
        <>
            <div className="relative justify-between items-center bg-gray-200 flex flex-row sm:flex-col flex-nowrap shadow h-1/6 sm:h-dvh w-full sm:w-1/12">
                <span className="sm:p-8 w-min h-fit inline-block">
                    <div className="font-sans font-bold text-xl/normal w-min">{props.timeText}</div>
                    <div className="font-sans font-normal text-xs/snug w-min">Total duration</div>
                </span>
                <div class="justify-around flex flex-row sm:flex-col flex-auto items-center max-w-4/6 sm:w-min">
                {props.menus && props.menus.length ? (
                    props.menus.map((menu, index) => (
                        <button 
                            className="w-22 text-center font-sans font-normal text-[#FAFAFC] text-xs/snug rounded-4xl box-border border cursor-pointer shadow transition-shadow bg-gradient-to-r from-[#764BFF] to-[#7BB7F1] py-4 px-3"
                            onClick={menu.action}
                        >{`${menu.title}`}</button>
                    ))
                ) : (
                    <></>
                )}
                {props.session.recording && !props.fromClient ? (
                    <span
                        className="bottom-2"
                        onClick={props.onEndSession}
                    >
                        <button className={style["end-button"]}>End</button>
                    </span>
                ) : (
                    <></>
                )}
                </div>
            </div>

            <GenericDialogBox show={props.sessionEnding}>
                <div className={style["dialog-content"]}>
                    <div className={style2["dialog-heading"]}>
                        Session Ending...
                    </div>
                    <div className={style["dialog-spinner"]}>
                        <AppSpinner></AppSpinner>
                    </div>
                </div>
            </GenericDialogBox>
        </>
    )
}

export { AppSessionPage }
