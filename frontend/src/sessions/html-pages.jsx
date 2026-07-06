import { useState, useEffect } from "react"
import { EmptyState } from "../components/empty-state"
import { formatDate } from "../globals"
import { ErrorDialog } from "../components/error-dialog"
import { useNavigate } from "react-router-dom"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component"
import { SessionService } from "../services/session-service"
import { SessionModel } from "../models/session"
import style from "./sessions.module.css"
import style2 from "../components/context-menu/context-menu.module.css"
import FolderIcon from "../Icons/Folder"
import MicIcon from "../Icons/Mic"
import { Camera, Chevron, Refresh, Upload } from "@/Icons"
import { StatusPill } from "../components/status-pill"
import { SkeletonRows } from "../components/skeleton"
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel, btnPrimary, btnSecondary, btnSecondarySm, btnDangerOutlineSm } from "../components/dialog-styles"

// Row wrapper (border/bg/hover) is a column so the expandable pod panel can sit
// below the horizontal row content.

const rowClass =
    "group flex flex-col rounded-lg border border-tiilt-line bg-white transition hover:border-tiilt hover:shadow-card-hover"
const rowInnerClass = "flex items-center gap-2.5 px-3 py-1.5"
const menuItemClass = style2["menu-item"]
const menuDangerClass = `${style2["menu-item"]} ${style2["red"]}`

const SORT_OPTIONS = [
    { value: "date-desc", label: "Newest first" },
    { value: "date-asc", label: "Oldest first" },
    { value: "length-desc", label: "Longest first" },
    { value: "length-asc", label: "Shortest first" },
    { value: "name-asc", label: "Name (A–Z)" },
]

function FilterTab({ active, onClick, children }) {
    return (
        <button
            onClick={onClick}
            className={
                "cursor-pointer rounded-md px-3 py-1 text-sm font-semibold transition " +
                (active
                    ? "bg-white text-tiilt shadow-card"
                    : "text-tiilt-muted hover:text-tiilt-ink")
            }
        >
            {children}
        </button>
    )
}

function SortControl({
    value,
    onChange,
    count,
    videoFilter,
    setVideoFilter,
    videoCount,
    audioCount,
    searchQuery,
    setSearchQuery,
}) {
    return (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sessions…"
                aria-label="Search sessions by name"
                className="h-9 w-full rounded-lg border border-tiilt-line bg-white px-3 text-sm text-tiilt-ink transition outline-none placeholder:text-tiilt-muted focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 sm:order-last sm:w-56"
            />
            <div className="flex items-center gap-1 rounded-lg border border-tiilt-line bg-tiilt-ground p-1">
                <FilterTab
                    active={videoFilter === "all"}
                    onClick={() => setVideoFilter("all")}
                >
                    All {count}
                </FilterTab>
                <FilterTab
                    active={videoFilter === "video"}
                    onClick={() => setVideoFilter("video")}
                >
                    Video {videoCount}
                </FilterTab>
                <FilterTab
                    active={videoFilter === "audio"}
                    onClick={() => setVideoFilter("audio")}
                >
                    Audio only {audioCount}
                </FilterTab>
            </div>
            <label className="flex items-center gap-2 text-sm text-tiilt-muted">
                Sort by
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="cursor-pointer rounded-lg border border-tiilt-line bg-white py-1.5 pr-8 pl-3 text-sm font-semibold text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                >
                    {SORT_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                            {o.label}
                        </option>
                    ))}
                </select>
            </label>
        </div>
    )
}


// Upload a recording to be analyzed: creates a session+pod server-side and
// auto-queues the full analysis. Self-contained state so failures are VISIBLE
// (the previous prompt-based flow could fail silently).
function UploadVideoButton() {
    const [busy, setBusy] = useState(false)
    const [note, setNote] = useState("")
    const onPick = (e) => {
        const file = e.target.files && e.target.files[0]
        e.target.value = ""
        if (!file) return
        setBusy(true)
        setNote("Uploading " + file.name + "…")
        const fd = new FormData()
        fd.append("video", file)
        fd.append("name", file.name.replace(/\.[^.]+$/, ""))
        fetch("/api/v1/sessions/upload_video", {
            method: "POST",
            body: fd,
            credentials: "include",
        })
            .then(async (r) => {
                if (r.status === 200) {
                    setNote("Uploaded — analysis queued. Reloading…")
                    setTimeout(() => window.location.reload(), 900)
                } else {
                    const t = await r.text().catch(() => "")
                    setBusy(false)
                    setNote("Upload failed (" + r.status + "): " + t.slice(0, 120))
                }
            })
            .catch((err) => {
                setBusy(false)
                setNote("Upload failed: " + err)
            })
    }
    return (
        <label
            className={
                "flex items-center gap-1.5 rounded-lg border border-tiilt-line bg-white px-4 py-2 text-sm font-semibold text-tiilt-ink transition focus-within:border-tiilt focus-within:ring-[3px] focus-within:ring-tiilt/30 active:translate-y-px " +
                (busy ? "cursor-wait opacity-60" : "cursor-pointer hover:border-tiilt hover:bg-tiilt-soft")
            }
            title={note || "Upload a webm/mp4 recording to analyze"}
        >
            <Upload />
            {busy ? "Uploading…" : "Upload video"}
            {note && !busy ? (
                <span className="max-w-56 truncate text-xs font-normal text-tiilt-danger">{note}</span>
            ) : null}
            {/* sr-only (not display:none) keeps the file input keyboard-focusable */}
            <input type="file" accept="video/webm,video/mp4" className="sr-only" disabled={busy} onChange={onPick} />
        </label>
    )
}

function FolderRow({ folder, count, onOpen, openFolderDialog }) {
    return (
        <li className={rowClass}>
            <div className={rowInnerClass}>
                <span className="flex h-8 w-8 flex-none items-center justify-center rounded-md bg-tiilt-soft text-tiilt">
                    <FolderIcon />
                </span>
                <button
                    onClick={() => onOpen(folder.id)}
                    className="min-w-0 grow cursor-pointer truncate text-left text-base font-semibold text-tiilt-ink"
                >
                    {folder.name}
                    {count != null ? (
                        <span className="ml-2 text-xs font-normal text-tiilt-muted">
                            {count} {count === 1 ? "session" : "sessions"}
                        </span>
                    ) : null}
                </button>
                <div className="flex-none">
                    <AppContextMenu label={`Options for folder ${folder.name}`}>
                        <button
                            role="menuitem"
                            className={menuItemClass}
                            onClick={() => openFolderDialog("RenameFolder", folder)}
                        >
                            Edit Name
                        </button>
                        <button
                            role="menuitem"
                            className={menuItemClass}
                            onClick={() => openFolderDialog("MoveFolder", folder)}
                        >
                            Move To...
                        </button>
                        <button
                            role="menuitem"
                            className={menuDangerClass}
                            onClick={() => openFolderDialog("DeleteFolder", folder)}
                        >
                            Delete
                        </button>
                    </AppContextMenu>
                </div>
            </div>
        </li>
    )
}

// Lazily fetches a session's pods and lists each one as a clickable row that
// opens the pod's detail page, with duration, participant count and status.
function PodDurations({ sessionId }) {
    const [pods, setPods] = useState(null) // null = loading
    const [error, setError] = useState(false)
    const navigate = useNavigate()
    useEffect(() => {
        let alive = true
        new SessionService().getSessionDevices(sessionId).then(
            (response) => {
                if (response.status === 200) {
                    response.json().then((devices) => {
                        if (alive) setPods(devices)
                    })
                } else if (alive) {
                    setError(true)
                }
            },
            () => {
                if (alive) setError(true)
            },
        )
        return () => {
            alive = false
        }
    }, [sessionId])

    if (error || pods === null || pods.length === 0) {
        const msg = error
            ? "Couldn't load pods."
            : pods === null
              ? "Loading pods…"
              : "No pods in this session."
        return (
            <div className="border-t border-tiilt-line px-3 py-2 pl-[3.25rem] text-xs text-tiilt-muted">
                {msg}
            </div>
        )
    }

    return (
        <ul className="flex flex-col gap-0.5 border-t border-tiilt-line px-2 py-1.5 pl-[3rem]">
            {pods.map((pod) => (
                <li key={pod.id}>
                    <button
                        onClick={() =>
                            navigate(`/sessions/${sessionId}/pods/${pod.id}`)
                        }
                        className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-left text-xs transition hover:bg-tiilt-soft"
                    >
                        <span
                            className={
                                "min-w-0 grow truncate font-medium " +
                                (pod.has_data === false
                                    ? "text-tiilt-muted"
                                    : "text-tiilt-ink")
                            }
                        >
                            {pod.name || `Pod ${pod.id}`}
                        </span>
                        {pod.has_data === false ? (
                            <StatusPill tone="neutral">
                                No data recorded
                            </StatusPill>
                        ) : (
                            <>
                                {pod.speaker_count > 0 ? (
                                    <span className="flex-none text-tiilt-muted">
                                        {pod.speaker_count}{" "}
                                        {pod.speaker_count === 1
                                            ? "participant"
                                            : "participants"}
                                    </span>
                                ) : null}
                                {pod.analysis_running ? (
                                    <StatusPill tone="orange" pulse>
                                        Analyzing…
                                    </StatusPill>
                                ) : pod.posthoc_analyzed_date ? (
                                    <StatusPill tone="teal">
                                        Analyzed
                                    </StatusPill>
                                ) : null}
                                <span className="flex-none font-ahamono tabular-nums text-tiilt-muted">
                                    {SessionModel.formatDuration(pod.duration)}
                                </span>
                            </>
                        )}
                        <Chevron size={12} className="flex-none text-tiilt-muted" />
                    </button>
                </li>
            ))}
        </ul>
    )
}

function SessionRow({ session, onOpen, openSessionDialog, endSession, checked, onToggle }) {
    const [expanded, setExpanded] = useState(false)
    const hasPods = session.pod_count != null && session.pod_count > 0
    return (
        <li className={rowClass}>
            <div className={rowInnerClass}>
            <input
                type="checkbox"
                checked={!!checked}
                onChange={onToggle}
                aria-label={`Select session ${session.title}`}
                className="h-4 w-4 flex-none cursor-pointer accent-tiilt"
            />
            <span
                className={
                    "flex h-8 w-8 flex-none items-center justify-center rounded-md " +
                    (session.recording
                        ? "bg-tiilt-danger-soft text-tiilt-danger"
                        : "bg-tiilt-soft text-tiilt")
                }
            >
                {session.has_video ? (
                    <Camera />
                ) : (
                    <svg width="20" height="20" viewBox="0 0 20 30">
                        <MicIcon fill="currentColor" />
                    </svg>
                )}
            </span>
            <button
                onClick={() => onOpen(session)}
                className="flex min-w-0 grow cursor-pointer flex-col text-left"
            >
                <span
                    title={session.title}
                    className="truncate text-base font-semibold text-tiilt-ink"
                >
                    {session.title}
                </span>
                <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-tiilt-muted">
                    <span className="whitespace-nowrap">
                        {formatDate(session.creation_date)}
                    </span>
                    <span aria-hidden="true">·</span>
                    <span className="font-ahamono tabular-nums whitespace-nowrap">
                        {session.lengthFormatted}
                    </span>
                    {session.participant_count > 0 ? (
                        <>
                            <span aria-hidden="true">·</span>
                            <span className="whitespace-nowrap">
                                {session.participant_count}{" "}
                                {session.participant_count === 1
                                    ? "participant"
                                    : "participants"}
                            </span>
                        </>
                    ) : null}
                    {session.analysis_running ? (
                        <StatusPill
                            tone="orange"
                            pulse
                            title="A full analysis is running right now"
                        >
                            Analyzing…
                        </StatusPill>
                    ) : null}
                    {session.has_posthoc ? (
                        <StatusPill
                            tone="teal"
                            title="Post-hoc analysis has been run for this session"
                        >
                            <Refresh />
                            Re-analyzed
                        </StatusPill>
                    ) : null}
                    {hasPods ? (
                        <span
                            title="Pods (participant groups) recorded in this session"
                            className="flex flex-none items-center gap-1 rounded-full bg-tiilt-soft px-1.5 py-0.5 font-semibold whitespace-nowrap text-tiilt"
                        >
                            {session.pod_count}{" "}
                            {session.pod_count === 1 ? "pod" : "pods"}
                        </span>
                    ) : null}
                </span>
            </button>
            {session.recording ? (
                <StatusPill tone="danger" dot className="text-xs">
                    Live
                </StatusPill>
            ) : null}
            {hasPods ? (
                <button
                    onClick={() => setExpanded((v) => !v)}
                    title={expanded ? "Hide pods" : "Show pod durations"}
                    aria-expanded={expanded}
                    className="flex h-7 w-7 flex-none items-center justify-center rounded-md text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                >
                    <Chevron
                        direction="down"
                        style={{
                            transform: expanded ? "rotate(180deg)" : "none",
                            transition: "transform 0.15s",
                        }}
                    />
                </button>
            ) : null}
            <div className="flex-none">
                <AppContextMenu label={`Options for session ${session.title}`}>
                    <button
                        role="menuitem"
                        className={menuItemClass}
                        onClick={() =>
                            openSessionDialog("RenameSession", session)
                        }
                    >
                        Edit Name
                    </button>
                    <button
                        role="menuitem"
                        className={menuItemClass}
                        onClick={() =>
                            openSessionDialog("MoveSession", session)
                        }
                    >
                        Move To...
                    </button>
                    {!session.recording ? (
                        <button
                            role="menuitem"
                            className={menuDangerClass}
                            onClick={() =>
                                openSessionDialog("DeleteSession", session)
                            }
                        >
                            Delete
                        </button>
                    ) : (
                        <button
                            role="menuitem"
                            className={menuDangerClass}
                            onClick={() => endSession(session)}
                        >
                            End
                        </button>
                    )}
                </AppContextMenu>
            </div>
            </div>
            {expanded ? <PodDurations sessionId={session.id} /> : null}
        </li>
    )
}

function DiscussionSessionPage(props) {
    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Manage Sessions"}
                    leftText={false}
                    rightText={""}
                    nav={props.navigateToHomescreen}
                />

                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-3xl px-4 py-8">
                        {props.isLoading ? (
                            <SkeletonRows rows={8} className="mt-14" />
                        ) : (
                            <></>
                        )}
                        {!props.isLoading &&
                        props.sessions.length === 0 &&
                        props.folders.length === 0 ? (
                            <EmptyState
                                title="No sessions or folders"
                                subtitle="Record your first session or create a folder with the buttons above."
                            />
                        ) : (
                            <></>
                        )}

                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                            <nav className="flex min-w-0 items-center gap-2 text-lg">
                                {props.breadcrumbs.length > 0 ? (
                                    <button
                                        onClick={props.goBackToPrevious}
                                        className="flex items-center gap-2 font-semibold text-tiilt hover:underline"
                                    >
<Chevron direction="left" size={16} />
                                        Home
                                    </button>
                                ) : (
                                    <span className="font-semibold text-tiilt-ink">
                                        Home
                                    </span>
                                )}
                                {props.breadcrumbs.length > 1 ? (
                                    <span className="text-tiilt-muted">
                                        / … /
                                    </span>
                                ) : props.breadcrumbs.length === 1 ? (
                                    <span className="text-tiilt-muted">/</span>
                                ) : (
                                    <></>
                                )}
                                {props.breadcrumbs.length > 0 ? (
                                    <span className="max-w-60 truncate font-semibold text-tiilt-ink">
                                        {
                                            props.breadcrumbs[
                                                props.breadcrumbs.length - 1
                                            ].name
                                        }
                                    </span>
                                ) : (
                                    <></>
                                )}
                            </nav>
                            <div className="flex flex-wrap justify-end gap-2">
                                <button
                                    className={btnSecondary + " flex items-center gap-1.5"}
                                    onClick={() => props.openFolderDialog("NewFolder")}
                                >
                                    <FolderIcon className="h-4 w-4" />
                                    New folder
                                </button>
                                <UploadVideoButton />
                                <button
                                    className={btnPrimary + " flex items-center gap-1.5"}
                                    onClick={props.newRecording}
                                >
                                    <span aria-hidden="true" className="text-base leading-none">+</span>
                                    New session
                                </button>
                            </div>
                        </div>

                        {!props.isLoading ? (
                            <div className="mb-4 rounded-lg border border-tiilt-line bg-tiilt-soft/40 px-3.5 py-2.5 text-xs leading-relaxed text-tiilt-muted">
                                <span className="font-semibold text-tiilt-ink">
                                    Sessions vs. pods:
                                </span>{" "}
                                A{" "}
                                <span className="font-semibold">session</span> is
                                one recorded session. Each{" "}
                                <span className="font-semibold">pod</span> is a
                                participant group (device) within that session — a
                                session can have several pods running at once.
                                Expand a session to see its pods, and click any
                                pod to open its analysis.
                            </div>
                        ) : null}

                        {!props.isLoading &&
                        props.displayedFolders.length > 0 ? (
                            <ul className="flex flex-col gap-1.5">
                                {props.displayedFolders.map((folder, index) => (
                                    <FolderRow
                                        key={index}
                                        folder={folder}
                                        count={(props.sessions || []).filter((x) => x.folder === folder.id).length}
                                        onOpen={props.displayFolder}
                                        openFolderDialog={
                                            props.openFolderDialog
                                        }
                                    />
                                ))}
                            </ul>
                        ) : (
                            <></>
                        )}

                        {!props.isLoading &&
                        props.videoCount + props.audioCount > 0 ? (
                            <div className="mt-4">
                                <SortControl
                                    value={props.sortBy}
                                    onChange={props.setSortBy}
                                    searchQuery={props.searchQuery}
                                    setSearchQuery={props.setSearchQuery}
                                    count={props.videoCount + props.audioCount}
                                    videoFilter={props.videoFilter}
                                    setVideoFilter={props.setVideoFilter}
                                    videoCount={props.videoCount}
                                    audioCount={props.audioCount}
                                />
                                {props.selectedCount > 0 ? (
                                    <div className="mb-3 flex flex-wrap items-center gap-3 rounded-lg border border-tiilt-line bg-tiilt-soft/50 px-3.5 py-2 text-sm">
                                        <span className="font-semibold text-tiilt-ink">
                                            {props.selectedCount} selected
                                        </span>
                                        <button
                                            onClick={() => props.openBulkDialog("MoveSessions")}
                                            className={btnSecondarySm}
                                        >
                                            Move to…
                                        </button>
                                        <button
                                            onClick={() => props.openBulkDialog("DeleteSessions")}
                                            className={btnDangerOutlineSm}
                                        >
                                            Delete…
                                        </button>
                                        <button
                                            onClick={props.clearSelected}
                                            className="ml-auto text-xs font-semibold text-tiilt-muted transition hover:text-tiilt"
                                        >
                                            Clear
                                        </button>
                                    </div>
                                ) : null}
                                {props.displayedSessions.length > 0 ? (
                                    <ul className="flex flex-col gap-1.5">
                                        {props.displayedSessions.map(
                                            (session, index) => (
                                                <SessionRow
                                                    key={index}
                                                    session={session}
                                                    checked={props.selectedIds[session.id]}
                                                    onToggle={() => props.toggleSelected(session.id)}
                                                    onOpen={props.goToSession}
                                                    openSessionDialog={
                                                        props.openSessionDialog
                                                    }
                                                    endSession={
                                                        props.endSession
                                                    }
                                                />
                                            ),
                                        )}
                                    </ul>
                                ) : (
                                    <div className="py-8 text-center text-sm text-tiilt-muted">
                                        No{" "}
                                        {props.videoFilter === "video"
                                            ? "sessions with video"
                                            : "audio-only sessions"}
                                        .
                                    </div>
                                )}
                            </div>
                        ) : (
                            <></>
                        )}

                        {(props.folders.length > 0 ||
                            props.sessions.length > 0) &&
                        !props.isLoading ? (
                            <div>
                                {props.displayedFolders.length === 0 &&
                                props.displayedSessions.length === 0 ? (
                                    <EmptyState
                                        title="This folder is empty"
                                        subtitle="Move sessions here or record a new one."
                                    />
                                ) : (
                                    <></>
                                )}
                            </div>
                        ) : (
                            <></>
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
                {props.currentForm === "RenameSession" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Update Session Name:
                        </div>
                        <input
                            id="txtName"
                            defaultValue={props.selectedSession.title}
                            aria-label="Session name"
                            className={dlgInput}
                            maxLength="64"
                        />
                        <div>
                            {props.invalidName
                                ? "Your proposed rename is invalid."
                                : ""}
                        </div>
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.changeSessionName(
                                    document.getElementById("txtName").value,
                                )
                            }
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
                ) : (
                    <></>
                )}

                {props.currentForm === "RenameFolder" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Update Folder Name:
                        </div>
                        <input
                            id="txtName"
                            defaultValue={props.selectedFolder.name}
                            aria-label="Folder name"
                            className={dlgInput}
                            maxLength="64"
                        />
                        <div>
                            {props.invalidName
                                ? "Your proposed rename is invalid."
                                : ""}
                        </div>
                        <button
                            className={dlgPrimary}
                            onClick={() => {
                                props.changeFolderName(
                                    document.getElementById("txtName").value,
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
                ) : (
                    <></>
                )}

                {props.currentForm === "DeleteSession" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={style["dialog-body"]}>
                            Are you sure you want to permanently delete this
                            session?
                        </div>
                        <button
                            className={style["delete-button"]}
                            onClick={props.deleteSession}
                        >
                            {" "}
                            Delete
                        </button>
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            {" "}
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "DeleteFolder" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            {" "}
                            Delete Folder
                        </div>
                        <div className={style["dialog-body"]}>
                            {" "}
                            Are you sure you want to permanently delete this
                            folder and all of its contents?
                        </div>
                        <button
                            className={style["delete-button"]}
                            onClick={props.deleteFolder}
                        >
                            {" "}
                            Delete
                        </button>
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            {" "}
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "NewFolder" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            {" "}
                            Add New Folder
                        </div>
                        <input
                            placeholder="Enter new folder name"
                            aria-label="New folder name"
                            id="txtName"
                            className={dlgInput}
                            maxLength="64"
                        />
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.addFolder(
                                    document.getElementById("txtName").value,
                                    props.breadcrumbs.length
                                        ? props.breadcrumbs[
                                              props.breadcrumbs.length - 1
                                          ].id
                                        : null,
                                )
                            }
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
                ) : (
                    <></>
                )}

                {props.currentForm === "MoveFolder" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Move Folder
                        </div>
                        <AppFolderSelectComponent
                            selectableFolders={props.selectableFolders}
                            setFolderSelect={props.setFolderSelect}
                            breadcrumbs={props.breadcrumbs}
                        />
                        {/* <app-folder-select #folderSelect [folders] = "selectableFolders" ></app - folder - select > */}
                        {props.folderSelect !== null ? (
                            <button
                                className={dlgPrimary}
                                onClick={() =>
                                    props.moveFolder(props.folderSelect)
                                }
                            >
                                {" "}
                                OK
                            </button>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            {" "}
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "MoveSession" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Move Session
                        </div>
                        <AppFolderSelectComponent
                            selectableFolders={props.selectableFolders}
                            setFolderSelect={props.setFolderSelect}
                            breadcrumbs={props.breadcrumbs}
                        />
                        {/* <app-folder-select #folderSelect [folders] = "selectableFolders" ></app - folder - select > */}
                        {props.folderSelect !== null ? (
                            <button
                                className={dlgPrimary}
                                onClick={() =>
                                    props.moveSession(props.folderSelect)
                                }
                            >
                                {" "}
                                OK
                            </button>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            {" "}
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "MoveSessions" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Move {props.selectedCount} session{props.selectedCount === 1 ? "" : "s"}
                        </div>
                        <AppFolderSelectComponent
                            selectableFolders={props.selectableFolders}
                            setFolderSelect={props.setFolderSelect}
                            breadcrumbs={props.breadcrumbs}
                        />
                        {props.folderSelect !== null ? (
                            <button
                                className={dlgPrimary}
                                onClick={() =>
                                    props.bulkMoveSessions(props.folderSelect)
                                }
                            >
                                Move
                            </button>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "DeleteSessions" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Delete {props.selectedCount} session{props.selectedCount === 1 ? "" : "s"}
                        </div>
                        <div className={style["dialog-body"]}>
                            This permanently deletes the selected sessions and
                            all of their recordings and analyses. This cannot
                            be undone.
                        </div>
                        <button
                            className={style["delete-button"]}
                            onClick={props.bulkDeleteSessions}
                        >
                            Delete {props.selectedCount}
                        </button>
                        <button
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "Loading" ? (
                    <div
                        className={dlgWindow}
                        style={{ minWidth: "min(20rem, 76vw)" }}
                    >
                        <div className={dlgHeading}>
                            Loading...please wait...
                        </div>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>

            <ErrorDialog message={props.alertMessage} show={props.showAlert} onClose={props.closeAlert} />
        </>
    )
}

export { DiscussionSessionPage }
