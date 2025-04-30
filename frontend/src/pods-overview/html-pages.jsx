import React from "react"
import style from "./pods-overview.module.css"
import style2 from "../dialog/dialog.module.css"
import style3 from "../session-toolbar/session-toolbar.module.css"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { adjDim } from "../myhooks/custom-hooks"

import MicIcon from "../Icons/Mic"

function PodsOverviewPages(props) {
    const POD_ON_COLOR = "#FF6655"
    const POD_OFF_COLOR = "#D0D0D0"
    const GLOW_COLOR = "#ffc3bd"

    return (
        <>
            <div className="main-container">
                <Appheader
                    title={"Overview"}
                    leftText={false}
                    rightText={props.righttext}
                    rightEnabled={props.rightenabled}
                    rightTextClick={() => {
                        props.openDialog("Passcode")
                    }}
                    nav={props.navigateToSessions}
                />
                <div className="toolbar-view-container">
                    {props.session !== null ? (
                        <AppSessionToolbar
                            session={props.session}
                            closingSession={props.onSessionClosing}
                            menus={[
                                {
                                    title: "Download",
                                    action: () => props.exportSession(),
                                },
                                {
                                    title: "Graph",
                                    action: () => props.goToGraph(),
                                },
                            ]}
                        ></AppSessionToolbar>
                    ) : (
                        <></>
                    )}
                    <div className="infographics-container mt-2 grow overflow-y-auto">
                        {props.sessionDevices === null ? (
                            <div className={style["load-text"]}>Loading...</div>
                        ) : (
                            <></>
                        )}
                        {props.sessionDevices !== null &&
                        Object.keys(props.sessionDevices).length === 0 ? (
                            <div className={style["load-text"]}>
                                {" "}
                                No pods specified
                            </div>
                        ) : (
                            <></>
                        )}
                        {props.sessionDevices !== null ? (
                            props.sessionDevices.map((device, index) => (
                                <div
                                    key={index}
                                    onClick={() => props.goToDevice(device)}
                                    className={style["pod-overview-button"]}
                                >
                                    <svg
                                        className={style["pod-overview-icon"]}
                                        width="80px"
                                        height="80px"
                                        viewBox="-40 -40 80 80"
                                    >
                                        <svg
                                            x="-8.5"
                                            y="-13.5"
                                            width="17"
                                            height="27"
                                            viewBox="0 0 17 27"
                                        >
                                            <MicIcon
                                                fill={
                                                    device.connected
                                                        ? POD_ON_COLOR
                                                        : POD_OFF_COLOR
                                                }
                                            ></MicIcon>
                                        </svg>
                                        {device.button_pressed ? (
                                            <svg>
                                                <circle
                                                    className={style.svgpulse}
                                                    x="0"
                                                    y="0"
                                                    r="33.5"
                                                    fill-opacity="0"
                                                    stroke={GLOW_COLOR}
                                                ></circle>{" "}
                                            </svg>
                                        ) : (
                                            <></>
                                        )}
                                        <svg>
                                            <circle
                                                x="0"
                                                y="0"
                                                r="30.5"
                                                fillOpacity="0"
                                                strokeWidth="3"
                                                stroke={
                                                    device.connected
                                                        ? POD_ON_COLOR
                                                        : POD_OFF_COLOR
                                                }
                                            ></circle>
                                        </svg>
                                    </svg>
                                    <div>{device.name}</div>
                                </div>
                            ))
                        ) : (
                            <></>
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
                {props.currentForm === "AddDevice" ? (
                    <div>
                        <div className={style2["dialog-heading"]}>
                            Add pod to Session
                        </div>
                        {props.devices.length > 0 ? (
                            <React.Fragment>
                                <select
                                    id="ddDevice"
                                    className={style["dropdown-input"]}
                                >
                                    {props.devices.map((device, index) => (
                                        <option
                                            key={index}
                                            defaultValue={device.id}
                                        >
                                            {device.name}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    className={style["basic-button"]}
                                    onClick={() =>
                                        props.addPodToSession(
                                            document.getElementById("ddDevice")
                                                .value,
                                        )
                                    }
                                >
                                    Add
                                </button>
                            </React.Fragment>
                        ) : (
                            <></>
                        )}
                        {props.devices.length === 0 ? (
                            <div className={style["unavailable-text"]}>
                                No devices available.
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["cancel-button"]}
                            onClick={props.closeDialog}
                        >
                            Close
                        </button>
                    </div>
                ) : (
                    <></>
                )}
                {props.currentForm === "Passcode" ? (
                    <div>
                        <div className={style2["dialog-heading"]}>
                            Passcode Settings
                        </div>
                        <button
                            className={style["basic-button"]}
                            onClick={() => props.copyPasscode()}
                        >
                            Copy
                        </button>
                        <button
                            className={style["basic-button"]}
                            onClick={() => props.setPasscodeState("lock")}
                        >
                            Lock
                        </button>
                        <button
                            className={style["basic-button"]}
                            onClick={() => props.setPasscodeState("unlock")}
                        >
                            Unlock
                        </button>
                        <button
                            className={style["basic-button"]}
                            onClick={() => props.setPasscodeState("refresh")}
                        >
                            Refresh
                        </button>
                        <button
                            className={style["cancel-button"]}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>
        </>
    )
}

export { PodsOverviewPages }
