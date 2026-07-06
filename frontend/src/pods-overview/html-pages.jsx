import React, { useState, useEffect } from "react"
import { SessionModel } from "../models/session"
import { dlgHeading, dlgBody, dlgLabel, dlgSelect, dlgPrimary, dlgCancel, dlgDanger, btnPrimarySm, btnDangerOutlineSm, btnSecondary } from "../components/dialog-styles"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component"
import { SkeletonRows } from "../components/skeleton"

import MicIcon from "../Icons/Mic"
import { Camera, Chevron } from "@/Icons"
import { StatusPill } from "../components/status-pill"
import { ToastStack } from "../components/toast"
import { QrCode } from "../components/qr-code"


// null (hide) for missing durations, else SessionModel's shared H:MM:SS.
function fmtDur(seconds) {
    if (seconds == null || isNaN(seconds)) return null
    return SessionModel.formatDuration(seconds)
}

function PodCard({ device, enrich, onOpen, checked, onToggle, queue, index, lastSpoke }) {
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
                    : "hover:border-tiilt hover:shadow-card-hover active:translate-y-px")
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
                        lastSpoke && Date.now() - lastSpoke < 30000 ? (
                            <StatusPill tone="teal" pulse className="text-[11px]">
                                Speaking
                            </StatusPill>
                        ) : (
                            <StatusPill tone="teal" dot className="text-[11px]">
                                Online
                            </StatusPill>
                        )
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

// Sticky status strip while recording: elapsed time, group count, code, End.
function RecordingBanner({ session, deviceCount, passcode, onEnd }) {
    const [, setTick] = useState(0)
    useEffect(() => {
        const t = setInterval(() => setTick((x) => x + 1), 1000)
        return () => clearInterval(t)
    }, [])
    const started = session.local_start_date || session.creation_date
    const secs = Math.max(0, Math.floor((Date.now() - new Date(started).getTime()) / 1000))
    const h = Math.floor(secs / 3600)
    const m = String(Math.floor((secs % 3600) / 60)).padStart(2, "0")
    const s = String(secs % 60).padStart(2, "0")
    return (
        <div className="flex w-full flex-none flex-wrap items-center gap-x-4 gap-y-1 border-b border-tiilt-line bg-tiilt-danger-soft/60 px-4 py-2 text-sm lg:px-8">
            <span className="flex items-center gap-1.5 font-semibold text-tiilt-danger">
                <span className="h-2 w-2 animate-pulse rounded-full bg-tiilt-danger" />
                Recording
            </span>
            <span className="font-ahamono tabular-nums text-tiilt-ink">
                {h > 0 ? `${h}:${m}:${s}` : `${m}:${s}`}
            </span>
            <span className="text-tiilt-muted">
                {deviceCount} {deviceCount === 1 ? "group" : "groups"}
            </span>
            {passcode ? (
                <span className="font-ahamono font-bold tracking-[0.2em] text-tiilt-ink">
                    {passcode}
                </span>
            ) : null}
            <button
                onClick={onEnd}
                className="ml-auto cursor-pointer rounded-lg border border-tiilt-danger/40 bg-white px-3 py-1 text-xs font-semibold text-tiilt-danger transition hover:border-tiilt-danger active:translate-y-px"
            >
                End session
            </button>
        </div>
    )
}

// Waiting room shown while the session is live but no group has joined yet:
// the share code/QR is the whole page instead of a hidden dialog.
function ProjectOverlay({ passcode, joinLink, onClose }) {
    useEffect(() => {
        const onKey = (e) => e.key === "Escape" && onClose()
        document.addEventListener("keydown", onKey)
        return () => document.removeEventListener("keydown", onKey)
    }, [onClose])
    return (
        /* role="dialog" also keeps the header's Escape-to-back handler from
           firing while the overlay is up (it skips Escape when a dialog is open). */
        <div
            role="dialog"
            aria-modal="true"
            aria-label="Projector view"
            className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-8 bg-white p-8"
        >
            <button
                onClick={onClose}
                aria-label="Close projector view"
                className="absolute top-4 right-5 cursor-pointer rounded-lg px-3 py-1.5 text-lg text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt-ink"
            >
                ✕
            </button>
            <div className="text-center font-ahamono text-2xl tracking-wide text-tiilt-muted">
                {joinLink.replace(/^https?:\/\//, "")}
            </div>
            <QrCode value={joinLink} size={340} />
            <div className="text-center">
                <div className="font-ahamono text-sm tracking-[0.3em] text-tiilt-muted uppercase">
                    Passcode
                </div>
                <div className="mt-2 font-ahamono text-7xl font-bold tracking-[0.35em] text-tiilt-ink">
                    {passcode}
                </div>
            </div>
        </div>
    )
}

function LobbyHero({ passcode, joinLink, copyJoinLink, onLock }) {
    const [projecting, setProjecting] = useState(false)
    return (
        <div className="mx-auto flex max-w-xl flex-col items-center gap-5 rounded-2xl border border-tiilt-line bg-white px-6 py-10 text-center shadow-pop">
            <div className="flex items-center gap-2 text-sm font-semibold text-tiilt-muted">
                <span className="h-2 w-2 animate-pulse rounded-full bg-tiilt-orange" />
                Waiting for groups to join…
            </div>
            <div className="rounded-xl bg-tiilt-soft/50 px-8 py-4">
                <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                    Passcode
                </div>
                <div className="mt-1 font-ahamono text-4xl font-bold tracking-[0.3em] text-tiilt-ink">
                    {passcode}
                </div>
            </div>
            <QrCode value={joinLink} size={190} />
            <div className="font-ahamono text-sm break-all text-tiilt-muted">
                {joinLink}
            </div>
            <div className="flex flex-wrap justify-center gap-2">
                <button className={dlgPrimary + " px-5"} onClick={copyJoinLink}>
                    Copy join link
                </button>
                <button className={btnSecondary} onClick={() => setProjecting(true)}>
                    ⛶ Project
                </button>
                <button className={btnSecondary} onClick={onLock}>
                    Lock joining
                </button>
            </div>
            <div className="text-xs text-tiilt-muted">
                Groups appear here the moment they connect.
            </div>
            {projecting ? (
                <ProjectOverlay
                    passcode={passcode}
                    joinLink={joinLink}
                    onClose={() => setProjecting(false)}
                />
            ) : null}
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

                {props.session && props.session.recording ? (
                    <RecordingBanner
                        session={props.session}
                        deviceCount={(props.sessionDevices || []).length}
                        passcode={props.passcode}
                        onEnd={() => props.openDialog("ConfirmEnd")}
                    />
                ) : null}
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
                                            className={btnDangerOutlineSm}
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
                                            className={btnPrimarySm + " whitespace-nowrap"}
                                        >
                                            Run analysis ({Object.values(props.selected || {}).filter(Boolean).length})
                                        </button>
                                    ) : null}
                                </span>
                            </div>
                            {props.sessionDevices !== null &&
                            props.initialized &&
                            Object.keys(props.sessionDevices).length === 0 ? (
                                props.passcode && props.session && !props.session.end_date ? (
                                    <LobbyHero
                                        passcode={props.passcode}
                                        joinLink={props.joinLink}
                                        copyJoinLink={props.copyJoinLink}
                                        onLock={() => props.setPasscodeState("lock")}
                                    />
                                ) : (
                                    <div className="rounded-xl border border-dashed border-tiilt-line py-16 text-center">
                                        <div className="text-base font-semibold text-tiilt-ink">
                                            No pods in this session
                                        </div>
                                        <div className="mt-1 text-sm text-tiilt-muted">
                                            Participants and recording devices
                                            will appear here once they join.
                                        </div>
                                    </div>
                                )
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
                                                lastSpoke={props.lastActivity && props.lastActivity[device.id]}
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
                    (props.currentForm === "ConfirmEnd" && (
                        <div className={dlgBody}>
                            <div className={dlgHeading}>End this session?</div>
                            <div className="text-sm text-tiilt-muted">
                                Recording stops for every group and the
                                passcode is retired. This can't be undone.
                            </div>
                            <button
                                className={dlgDanger}
                                onClick={props.endThisSession}
                            >
                                End session
                            </button>
                            <button
                                className={dlgCancel}
                                onClick={props.closeDialog}
                            >
                                Cancel
                            </button>
                        </div>
                    )) ||
                    (props.currentForm === "Passcode" && (
                        <div className={dlgBody}>
                            <div className={dlgHeading}>Share this session</div>
                            {props.passcode ? (
                                <>
                                    <div className="rounded-xl border border-tiilt-line bg-tiilt-soft/50 px-4 py-3 text-center">
                                        <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                            Passcode
                                        </div>
                                        <div className="mt-1 font-ahamono text-3xl font-bold tracking-[0.3em] text-tiilt-ink">
                                            {props.passcode}
                                        </div>
                                    </div>
                                    <QrCode value={props.joinLink} />
                                    <div className="rounded-lg border border-tiilt-line bg-white px-3 py-2 text-center font-ahamono text-sm break-all text-tiilt-muted">
                                        {props.joinLink}
                                    </div>
                                    <button
                                        className={dlgPrimary}
                                        onClick={() => props.copyJoinLink()}
                                    >
                                        Copy join link
                                    </button>
                                    <button
                                        className={dlgCancel}
                                        onClick={() => props.copyPasscode()}
                                    >
                                        Copy code only
                                    </button>
                                </>
                            ) : (
                                <div className="text-sm text-tiilt-muted">
                                    The session is locked — unlock it to get a
                                    passcode participants can join with.
                                </div>
                            )}
                            <div className="flex gap-2">
                                <button
                                    className={btnSecondary + " flex-1"}
                                    onClick={() => props.setPasscodeState("lock")}
                                >
                                    Lock
                                </button>
                                <button
                                    className={btnSecondary + " flex-1"}
                                    onClick={() => props.setPasscodeState("unlock")}
                                >
                                    Unlock
                                </button>
                                <button
                                    className={btnSecondary + " flex-1"}
                                    onClick={() =>
                                        props.setPasscodeState("refresh")
                                    }
                                >
                                    Refresh
                                </button>
                            </div>
                            <button
                                className={dlgCancel}
                                onClick={props.closeDialog}
                            >
                                Close
                            </button>
                        </div>
                    ))}
            </GenericDialogBox>
        </>
    )
}

export { PodsOverviewPages }
