import style from "./session-toolbar.module.css"
import style2 from "../dialog/dialog.module.css"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSpinner } from "../spinner/spinner-component"
import React from "react"
import { ScrollArea } from "@/components/ui/scroll-area"

function AppSessionPage(props) {
    return (
        <>
            <div className="side_bar">
                <div className="flex flex-none flex-col px-4 py-2 sm:w-full sm:items-start sm:px-6 sm:py-0">
                    <div className="font-sans text-2xl leading-none font-bold text-tiilt-ink tabular-nums sm:text-3xl">
                        {props.timeText}
                    </div>
                    <div className="mt-1 font-sans text-xs font-normal text-tiilt-muted sm:text-sm">
                        Total duration
                    </div>
                </div>

                {props.speakers && props.speakers.length !== 0 ? (
                    <div className="flex min-w-0 flex-1 flex-col px-3 sm:min-h-0 sm:w-full sm:px-6">
                        <div className="mb-2 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                            Participants
                            <span className="ml-1 text-tiilt-muted/70">
                                ({props.speakers.length})
                            </span>
                        </div>
                        <ScrollArea className="max-h-[220px] pr-1 sm:max-h-none sm:min-h-0 sm:flex-1">
                            <div className="flex flex-row gap-2 sm:flex-col">
                                {props.speakers.map((part, index) => (
                                    <button
                                        className="rounded-lg border border-tiilt-line bg-white px-3 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft sm:w-full sm:text-left"
                                        onClick={part.action}
                                        key={index}
                                    >{`${part.alias}`}</button>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>
                ) : (
                    <></>
                )}

                {props.seesions && props.seesions.length !== 0 ? (
                    <div className="flex min-w-0 flex-1 flex-col px-3 sm:w-full sm:flex-none sm:px-6">
                        <div className="mb-2 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                            Sessions
                        </div>
                        <ScrollArea className="max-h-[220px] pr-1">
                            <div className="flex flex-row gap-2 sm:flex-col">
                                {props.seesions.map((part, index) => (
                                    <button
                                        className="rounded-lg border border-tiilt-line bg-white px-3 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft sm:w-full sm:text-left"
                                        onClick={part.action}
                                        key={index}
                                    >{`${part.title}`}</button>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>
                ) : (
                    <></>
                )}

                <div className="flex flex-row items-center gap-2 px-3 sm:mt-auto sm:w-full sm:flex-col sm:px-6">
                    {props.menus && props.menus.length ? (
                        props.menus.map((menu, index) => (
                            <button
                                className="rounded-lg bg-tiilt px-4 py-2 text-sm font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px sm:w-full"
                                onClick={menu.action}
                                key={index}
                            >{`${menu.title}`}</button>
                        ))
                    ) : (
                        <></>
                    )}
                    <button
                        className="rounded-lg bg-tiilt-danger px-4 py-2 text-sm font-semibold text-white transition hover:brightness-90 active:translate-y-px disabled:hidden sm:w-full"
                        onClick={props.onEndSession}
                        disabled={!props.session.recording || props.fromClient}
                    >
                        End
                    </button>
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
