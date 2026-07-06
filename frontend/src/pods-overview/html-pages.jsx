import React from "react"
import { SessionModel } from "../models/session"
import { dlgHeading, dlgBody, dlgLabel, dlgSelect, dlgPrimary, dlgCancel } from "../components/dialog-styles"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { SkeletonRows } from "../components/skeleton"

import MicIcon from "../Icons/Mic"
import { Camera, Chevron } from "@/Icons"
import { StatusPill } from "../components/status-pill"


// null (hide) for missing durations, else SessionModel's shared H:MM:SS.
function fmtDur(seconds) {
    if (seconds == null || isNaN(seconds)) return null
    return SessionModel.formatDuration(seconds)
}

function PodCard({ device, enrich, onOpen, checked, onToggle, queue, index }) {
    const e = enrich || {}
    const name =
        device.name && String(device.name).trim()
            ? device.name
            : `Pod ${index + 1}`
    const dur = fmtDur(e.duration)
    return (
        <div className="flex w-full items-center gap-2">
        <input
            type="checkbox"
            checked={!!checked}
            onChange={onToggle}
            title="Select for batch analysis"
            aria-label={`Select ${name} for batch analysis`}
            className="h-4 w-4 flex-none cursor-pointer accent-tiilt"
        />
        <button
            onClick={e.has_data === false ? undefined : onOpen}
            disabled={e.has_data === false}
            title={
                e.has_data === false
                    ? "No data was recorded for this pod — there is nothing to view"
                    : undefined
            }
            className={
                "group flex w-full items-center gap-2.5 rounded-lg border border-tiilt-line bg-white px-3 py-2 text-left transition " +
                (e.has_data === false
                    ? "cursor-not-allowed opacity-60"
                    : "hover:border-tiilt hover:shadow-[0_10px_24px_-16px_rgba(42,23,74,0.5)] active:translate-y-px")
            }
        >
            <span
                className={
                    "relative flex h-9 w-9 flex-none items-center justify-center rounded-md " +
                    (device.connected
                        ? "bg-tiilt-danger-soft text-tiilt-danger"
                        : "bg-tiilt-soft text-tiilt-muted")
                }
            >
                {e.has_video ? (
                    <Camera />
                ) : (
                    <svg width="18" height="28" viewBox="0 0 17 27">
                        <MicIcon fill="currentColor" />
                    </svg>
                )}
                {device.button_pressed ? (
                    <span className="absolute -top-1 -right-1 h-3 w-3 animate-ping rounded-full bg-tiilt-orange" />
                ) : null}
            </span>
            <div className="min-w-0 grow">
                <div className="flex items-center gap-2">
                    <span
                        title={name}
                        className="min-w-0 truncate text-sm font-semibold text-tiilt-ink"
                    >
                        {name}
                    </span>
                    {device.connected ? (
                        <StatusPill tone="teal" dot className="text-[11px]">
                            Online
                        </StatusPill>
                    ) : null}
                </div>
                <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-tiilt-muted">
                    {queue === "error" ? (
                        <StatusPill tone="danger">Error</StatusPill>
                    ) : queue === "queued" ? (
                        <StatusPill tone="brand">Queued</StatusPill>
                    ) : queue === "running" || e.analysis_running ? (
                        <StatusPill tone="orange" pulse>
                            Running…
                        </StatusPill>
                    ) : e.has_data === false ? (
                        <StatusPill tone="neutral">No data</StatusPill>
                    ) : (device.posthoc_analyzed_date || e.posthoc_analyzed_date) ? (
                        <StatusPill
                            tone="teal"
                            title={"Full analysis run " + (device.posthoc_analyzed_date || e.posthoc_analyzed_date)}
                        >
                            Analyzed
                        </StatusPill>
                    ) : null}
                    {e.speaker_count > 0 ? (
                        <span>
                            {e.speaker_count}{" "}
                            {e.speaker_count === 1 ? "participant" : "participants"}
                        </span>
                    ) : null}
                    {dur ? (
                        <span className="font-ahamono tabular-nums">{dur}</span>
                    ) : null}
                </div>
            </div>
            <span
                aria-hidden="true"
                className="flex-none text-tiilt-muted transition group-hover:text-tiilt"
            >
                <Chevron size={12} />
            </span>
        </button>
        </div>
    )
}

// At-a-glance roll-up for the whole session (pods, analyzed, people, time).
function SessionStats({ devices, enriched }) {
    const en = enriched || {}
    const list = devices || []
    const analyzed = list.filter(
        (d) => (en[d.id] && en[d.id].posthoc_analyzed_date) || d.posthoc_analyzed_date,
    ).length
    const participants = list.reduce(
        (a, d) => a + ((en[d.id] && en[d.id].speaker_count) || 0),
        0,
    )
    const totalDur = list.reduce(
        (a, d) => a + ((en[d.id] && en[d.id].duration) || 0),
        0,
    )
    const tiles = [
        ["Pods", String(list.length)],
        ["Analyzed", `${analyzed}/${list.length}`],
        ["Participants", String(participants)],
        ["Recorded", totalDur > 0 ? fmtDur(totalDur) : "—"],
    ]
    return (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {tiles.map(([label, value]) => (
                <div
                    key={label}
                    className="rounded-xl border border-tiilt-line bg-white px-4 py-3"
                >
                    <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                        {label}
                    </div>
                    <div className="mt-1 text-xl font-semibold text-tiilt-ink tabular-nums">
                        {value}
                    </div>
                </div>
            ))}
        </div>
    )
}

// Bottom-right notification stack (analysis completions).
function ToastStack({ toasts, dismiss }) {
    if (!toasts || !toasts.length) return null
    return (
        <div
            role="status"
            aria-live="polite"
            className="fixed right-4 bottom-4 z-50 flex w-72 flex-col gap-2"
        >
            {toasts.map((t) => (
                <div
                    key={t.id}
                    className="flex items-center gap-2 rounded-xl border border-tiilt-line bg-white px-3.5 py-2.5 text-sm text-tiilt-ink shadow-[0_12px_28px_-12px_rgba(42,23,74,0.45)]"
                >
                    <span className="h-2 w-2 flex-none rounded-full bg-tiilt-teal" />
                    <span className="min-w-0 grow">{t.text}</span>
                    <button
                        onClick={() => dismiss(t.id)}
                        aria-label="Dismiss notification"
                        className="flex-none cursor-pointer rounded p-0.5 text-tiilt-muted transition hover:text-tiilt-ink"
                    >
                        ✕
                    </button>
                </div>
            ))}
        </div>
    )
}

function PodsOverviewPages(props) {
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Overview"}
                    leftText={false}
                    rightText={props.righttext}
                    rightPill={props.rightpill}
                    rightTextClick={() => {
                        props.openDialog("Passcode")
                    }}
                    nav={props.navigateToSessions}
                    escToBack={true}
                />

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
                        <div className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-8">
                            {props.sessionDevices !== null && props.initialized ? (
                                <SessionStats
                                    devices={props.sessionDevices}
                                    enriched={props.enriched}
                                />
                            ) : (
                                <SkeletonRows rows={6} className="mt-2" />
                            )}
                            <div className="mb-4 flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
                                <div>
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
                                    <div className="mt-0.5 text-xs text-tiilt-muted">
                                        Open a pod to view its analytics
                                    </div>
                                </div>
                                <span className="flex flex-none items-center gap-3 text-sm text-tiilt-muted">
                                    {Object.values(props.queueState || {}).some((v) => v === "queued" || v === "running") ||
                                    Object.values(props.enriched || {}).some((e) => e && e.analysis_running) ? (
                                        <button
                                            onClick={props.stopRuns}
                                            className="rounded-lg border border-tiilt-danger/40 bg-tiilt-danger-soft px-3 py-1.5 text-xs font-semibold text-tiilt-danger transition hover:border-tiilt-danger active:translate-y-px"
                                        >
                                            Stop runs
                                        </button>
                                    ) : null}
                                    <label className="flex cursor-pointer items-center gap-1.5 whitespace-nowrap text-xs">
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
                                            className="rounded-lg bg-tiilt px-3 py-1.5 text-xs font-semibold whitespace-nowrap text-white transition hover:bg-tiilt-deep active:translate-y-px"
                                        >
                                            Run analysis ({Object.values(props.selected || {}).filter(Boolean).length})
                                        </button>
                                    ) : null}
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
                                <div className="grid grid-cols-1 gap-1.5 lg:grid-cols-2 lg:gap-x-4">
                                    {props.sessionDevices.map(
                                        (device, index) => (
                                            <PodCard
                                                key={index}
                                                index={index}
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

            <ToastStack toasts={props.toasts} dismiss={props.dismissToast} />

            <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
                {(props.currentForm === "AddDevice" && (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add pod to Session</div>
                        {props.devices.length > 0 ? (
                            <React.Fragment>
                                <select id="ddDevice" aria-label="Pod to add" className={dlgSelect}>
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
                            <select id="format" aria-label="Download format" className={dlgSelect}>
                                <option value="">Select format</option>
                                <option value="csv">CSV</option>
                                <option value="json">JSON</option>
                            </select>
                            <select id="windowsize" aria-label="Window size in seconds" className={dlgSelect}>
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
                            <select id="datatype" aria-label="Data to download" className={dlgSelect}>
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
