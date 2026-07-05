import React from "react"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { AppSpinner } from "../spinner/spinner-component"

import MicIcon from "../Icons/Mic"

const dlgHeading = "mb-3 text-lg font-semibold text-tiilt-ink"
const dlgBody = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
const dlgLabel = "text-sm font-semibold text-tiilt-ink"
const dlgSelect =
    "h-11 w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 pr-8 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
const dlgPrimary =
    "mt-2 h-11 rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
const dlgCancel =
    "h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"

function fmtDur(seconds) {
    if (seconds == null || isNaN(seconds)) return null
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    const h = Math.floor(m / 60)
    return h > 0 ? `${h}:${String(m % 60).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`
}

function PodCard({ device, enrich, onOpen, checked, onToggle, queue }) {
    const e = enrich || {}
    return (
        <div className="flex w-full items-center gap-2">
        <input
            type="checkbox"
            checked={!!checked}
            onChange={onToggle}
            title="Select for batch analysis"
            className="h-4 w-4 flex-none cursor-pointer accent-tiilt"
        />
        <button
            onClick={onOpen}
            className="group flex w-full items-center gap-2.5 rounded-lg border border-tiilt-line bg-white px-3 py-1.5 text-left transition hover:border-tiilt hover:shadow-[0_10px_24px_-16px_rgba(42,23,74,0.5)] active:translate-y-px"
        >
            <span
                className={
                    "relative flex h-8 w-8 flex-none items-center justify-center rounded-md " +
                    (device.connected
                        ? "bg-tiilt-danger-soft text-tiilt-danger"
                        : "bg-tiilt-soft text-tiilt-muted")
                }
            >
                {e.has_video ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <rect x="2.5" y="6" width="12" height="12" rx="2.5" fill="currentColor" />
                        <path d="M16 10l5-3v10l-5-3z" fill="currentColor" />
                    </svg>
                ) : (
                    <svg width="18" height="28" viewBox="0 0 17 27">
                        <MicIcon fill="currentColor" />
                    </svg>
                )}
                {device.button_pressed ? (
                    <span className="absolute -top-1 -right-1 h-3 w-3 animate-ping rounded-full bg-tiilt-orange" />
                ) : null}
            </span>
            <span className="min-w-0 truncate text-sm font-semibold text-tiilt-ink">
                {device.name}
            </span>
            <span
                className={
                    "flex-none rounded-full px-1.5 py-0.5 text-[11px] font-semibold " +
                    (device.connected
                        ? "bg-tiilt-danger-soft text-tiilt-danger"
                        : "bg-tiilt-line/40 text-tiilt-muted")
                }
            >
                {device.connected ? "Online" : "Offline"}
            </span>
            <span className="grow" />
            <div className="flex flex-none items-center gap-2 text-xs text-tiilt-muted">
                {queue === "error" ? (
                    <span className="flex-none rounded-full bg-tiilt-danger-soft px-2 py-0.5 font-semibold text-tiilt-danger">
                        Error
                    </span>
                ) : queue === "queued" ? (
                    <span className="flex-none rounded-full bg-tiilt-soft px-2 py-0.5 font-semibold text-tiilt">
                        Queued
                    </span>
                ) : queue === "running" || e.analysis_running ? (
                    <span className="flex flex-none items-center gap-1 rounded-full bg-tiilt-orange/15 px-2 py-0.5 font-semibold text-tiilt-orange">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-tiilt-orange" />
                        Running…
                    </span>
                ) : e.has_data === false ? (
                    <span className="flex-none rounded-full bg-tiilt-line/40 px-2 py-0.5 font-semibold text-tiilt-muted">
                        No data
                    </span>
                ) : (device.posthoc_analyzed_date || e.posthoc_analyzed_date) ? (
                    <span
                        title={"Full analysis run " + (device.posthoc_analyzed_date || e.posthoc_analyzed_date)}
                        className="flex flex-none items-center gap-1 rounded-full bg-tiilt-teal/15 px-2 py-0.5 font-semibold text-tiilt-teal"
                    >
                        Analyzed
                    </span>
                ) : null}
                {e.speaker_count > 0 ? (
                    <span>
                        {e.speaker_count}{" "}
                        {e.speaker_count === 1 ? "participant" : "participants"}
                    </span>
                ) : null}
                {fmtDur(e.duration) ? (
                    <span className="font-ahamono tabular-nums">
                        {fmtDur(e.duration)}
                    </span>
                ) : null}
            </div>
            <span
                aria-hidden="true"
                className="flex-none text-tiilt-muted transition group-hover:text-tiilt"
            >
                ›
            </span>
        </button>
        </div>
    )
}

function PodsOverviewPages(props) {
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
                {props.sessionDevices === null || !props.initialized ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <div className="mb-3 text-base text-tiilt-muted">
                            Loading session data…
                        </div>
                        <AppSpinner />
                    </div>
                ) : (
                    <></>
                )}
                <div className="toolbar-view-container">
                    {props.session !== null ? (
                        <AppSessionToolbar
                            session={props.session}
                            closingSession={props.onSessionClosing}
                            menus={[
                                {
                                    title: "Download",
                                    action: () =>
                                        props.openDownloadOptionDialog(
                                            "selectdownloadoption",
                                        ),
                                },
                                {
                                    title: "Graph",
                                    action: () => props.goToGraph(),
                                },
                            ]}
                            participants={props.sessionSpeaker.map(
                                (speaker, index) => ({
                                    alias: speaker.alias,
                                    action: () =>
                                        props.goToSpeakerMetrics(speaker.id),
                                }),
                            )}
                        ></AppSessionToolbar>
                    ) : (
                        <></>
                    )}
                    <div className="min-h-0 grow overflow-y-auto">
                        <div className="mx-auto w-full max-w-3xl px-4 py-8">
                            <div className="mb-4 flex items-baseline justify-between gap-3">
                                <h2 className="text-lg font-semibold text-tiilt-ink">
                                    Pods
                                    {props.sessionDevices !== null &&
                                    props.initialized ? (
                                        <span className="ml-1.5 font-normal text-tiilt-muted">
                                            ({props.sessionDevices.length})
                                        </span>
                                    ) : (
                                        <></>
                                    )}
                                </h2>
                                <span className="flex items-center gap-3 text-sm text-tiilt-muted">
                                    {Object.values(props.queueState || {}).some((v) => v === "queued" || v === "running") ||
                                    Object.values(props.enriched || {}).some((e) => e && e.analysis_running) ? (
                                        <button
                                            onClick={props.stopRuns}
                                            className="rounded-lg border border-tiilt-danger/40 bg-tiilt-danger-soft px-3 py-1.5 text-xs font-semibold text-tiilt-danger transition hover:border-tiilt-danger active:translate-y-px"
                                        >
                                            Stop runs
                                        </button>
                                    ) : null}
                                    <label className="flex cursor-pointer items-center gap-1.5 text-xs">
                                        <input
                                            type="checkbox"
                                            className="h-4 w-4 cursor-pointer accent-tiilt"
                                            checked={
                                                (props.sessionDevices || []).length > 0 &&
                                                (props.sessionDevices || []).every(
                                                    (d) => props.selected && props.selected[d.id],
                                                )
                                            }
                                            onChange={() =>
                                                props.toggleSelectAll(
                                                    (props.sessionDevices || []).map((d) => d.id),
                                                )
                                            }
                                        />
                                        Select all
                                    </label>
                                    {Object.values(props.selected || {}).filter(Boolean).length > 0 ? (
                                        <button
                                            onClick={props.runSelected}
                                            className="rounded-lg bg-tiilt px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
                                        >
                                            Run full analysis on selected (
                                            {Object.values(props.selected || {}).filter(Boolean).length}
                                            )
                                        </button>
                                    ) : (
                                        <span>Open a pod to view its analytics</span>
                                    )}
                                </span>
                            </div>
                            {props.sessionDevices !== null &&
                            props.initialized &&
                            Object.keys(props.sessionDevices).length === 0 ? (
                                <div className="rounded-xl border border-dashed border-tiilt-line py-16 text-center">
                                    <div className="text-base font-semibold text-tiilt-ink">
                                        No pods in this session
                                    </div>
                                    <div className="mt-1 text-sm text-tiilt-muted">
                                        Participants and recording devices will
                                        appear here once they join.
                                    </div>
                                </div>
                            ) : (
                                <></>
                            )}
                            {props.sessionDevices !== null &&
                            props.initialized ? (
                                <div className="flex flex-col gap-1.5">
                                    {props.sessionDevices.map(
                                        (device, index) => (
                                            <PodCard
                                                key={index}
                                                device={device}
                                                enrich={props.enriched && props.enriched[device.id]}
                                                checked={props.selected && props.selected[device.id]}
                                                onToggle={() => props.toggleSelect(device.id)}
                                                queue={props.queueState && props.queueState[device.id]}
                                                onOpen={() =>
                                                    props.goToDevice(device)
                                                }
                                            />
                                        ),
                                    )}
                                </div>
                            ) : (
                                <></>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
                {(props.currentForm === "AddDevice" && (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add pod to Session</div>
                        {props.devices.length > 0 ? (
                            <React.Fragment>
                                <select id="ddDevice" className={dlgSelect}>
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
                                    className={dlgPrimary}
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
                            <div className="py-3 text-sm text-tiilt-muted">
                                No devices available.
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Close
                        </button>
                    </div>
                )) ||
                    (props.currentForm === "selectdownloadoption" && (
                        <div className={dlgBody}>
                            <div className={dlgHeading}>
                                Select the Data to Download:
                            </div>
                            <select id="format" className={dlgSelect}>
                                <option value="">Select format</option>
                                <option value="csv">CSV</option>
                                <option value="json">JSON</option>
                            </select>
                            <select id="windowsize" className={dlgSelect}>
                                <option value="">
                                    Select window size in secs
                                </option>
                                <option value="0">0</option>
                                <option value="10">10</option>
                                <option value="20">20</option>
                                <option value="30">30</option>
                                <option value="40">40</option>
                                <option value="50">50</option>
                                <option value="60">60</option>
                            </select>
                            <select id="datatype" className={dlgSelect}>
                                <option value="">
                                    Select data to download
                                </option>
                                <option value="audiometrics">
                                    Transcript Metrics
                                </option>
                                <option value="videometrics">
                                    Video Metrics
                                </option>
                                <option value="transcriptvideometrics">
                                    Transcript-Video Metrics
                                </option>
                            </select>

                            <button
                                className={dlgPrimary}
                                onClick={() => {
                                    props.downloadData(
                                        document.getElementById("windowsize")
                                            .value,
                                        document.getElementById("datatype")
                                            .value,
                                        document.getElementById("format").value,
                                    )
                                }}
                            >
                                {" "}
                                Confirm
                            </button>
                            <button
                                className={dlgCancel}
                                onClick={props.closeDialog}
                            >
                                {" "}
                                Cancel
                            </button>
                        </div>
                    )) ||
                    (props.currentForm === "Passcode" && (
                        <div className={dlgBody}>
                            <div className={dlgHeading}>Passcode Settings</div>
                            <button
                                className={dlgPrimary}
                                onClick={() => props.copyPasscode()}
                            >
                                Copy
                            </button>
                            <button
                                className={dlgPrimary}
                                onClick={() => props.setPasscodeState("lock")}
                            >
                                Lock
                            </button>
                            <button
                                className={dlgPrimary}
                                onClick={() => props.setPasscodeState("unlock")}
                            >
                                Unlock
                            </button>
                            <button
                                className={dlgPrimary}
                                onClick={() =>
                                    props.setPasscodeState("refresh")
                                }
                            >
                                Refresh
                            </button>
                            <button
                                className={dlgCancel}
                                onClick={props.closeDialog}
                            >
                                Cancel
                            </button>
                        </div>
                    ))}
            </GenericDialogBox>
        </>
    )
}

export { PodsOverviewPages }
