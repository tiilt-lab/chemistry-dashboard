import style from "./session-toolbar.module.css"
import style2 from "../dialog/dialog.module.css"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import React from "react"
import { isLargeScreen } from "../myhooks/custom-hooks"

function AppSessionPage(props) {
    return (
        <>
            <div className="relative flex h-1/6 w-full min-w-fit flex-row flex-nowrap items-center justify-between bg-gray-200 text-center shadow sm:h-full sm:w-1/6 sm:flex-col">
                <span className="m-3 inline-block h-fit w-min px-3 relative">
                    <div className="inline-block w-max font-sans text-xl/normal font-bold sm:text-3xl/loose">
                        {props.timeText}
                    </div>
                    <div className="inline-block w-max font-sans text-xs/snug font-normal sm:text-base/normal">
                        Total duration
                    </div>
                </span>
                <div class="flex relative max-w-4/6 flex-1 flex-row items-center justify-center sm:w-min sm:flex-col sm:max-w-full">
                    {props.menus && props.menus.length ? (
                        props.menus.map((menu, index) => (
                            <button
                                className="toolbar-button"
                                onClick={menu.action}
                            >{`${menu.title}`}</button>
                        ))
                    ) : (
                        <></>
                    )}
                </div>
                <button
                    className="relative mx-2 box-border w-19 cursor-pointer rounded-4xl border bg-[#FF6363] px-1 py-2 text-center font-sans text-base/normal font-normal text-[#FAFAFC] transition-shadow hover:shadow-2xl disabled:hidden sm:w-33 sm:text-xl/loose sm:mx-0 sm:my-5"
                    onClick={props.onEndSession}
                    disabled={!props.session.recording || props.fromClient}
                >
                    End
                </button>
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
