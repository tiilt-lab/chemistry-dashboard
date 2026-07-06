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
import { Camera, Chevron, Upload } from "@/Icons"
import { StatusPill } from "../components/status-pill"
import { SkeletonRows } from "../components/skeleton"
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel, btnPrimary, btnSecondary, btnSecondarySm, btnDangerOutlineSm } from "../components/dialog-styles"

const menuItemClass = style2["menu-item"]
const menuDangerClass = `${style2["menu-item"]} ${style2["red"]}`

// Search + filter chips; sorting moved into the table's column headers.
function SortControl({
    count,
    videoFilter,
    setVideoFilter,
    videoCount,
    audioCount,
    searchQuery,
    setSearchQuery,
}) {
    const chip = (value, label) => (
        <button
            onClick={() => setVideoFilter(value)}
            aria-pressed={videoFilter === value}
            className={
                "cursor-pointer rounded-full px-3 py-1 text-xs font-semibold whitespace-nowrap transition " +
                (videoFilter === value
                    ? "bg-tiilt text-white"
                    : "bg-tiilt-line/40 text-tiilt-muted hover:bg-tiilt-soft hover:text-tiilt")
            }
        >
            {label}
        </button>
    )
    return (
        <div className="mb-3 flex flex-wrap items-center gap-3">
            <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search all sessions…"
                aria-label="Search sessions by name, across all folders"
                className="h-10 w-full max-w-60 rounded-lg border border-tiilt-line bg-white px-3 text-sm text-tiilt-ink transition outline-none placeholder:text-tiilt-muted focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
            />
            <div className="flex items-center gap-1.5">
                {chip("all", `All ${count}`)}
                {chip("video", `Video ${videoCount}`)}
                {chip("audio", `Audio only ${audioCount}`)}
            </div>
        </div>
    )
}


// Small stat cards over ALL sessions (not just the open folder), matching
// the Students page pattern.
function SessionStats({ sessions }) {
    const all = sessions || []
    const live = all.filter((s) => s.recording).length
    const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
    const thisWeek = all.filter(
        (s) => s.creation_date && s.creation_date.getTime() > weekAgo,
    ).length
    const card = (label, value) => (
        <div className="flex-1 rounded-xl border border-tiilt-line bg-white px-4 py-3">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                {label}
            </div>
            <div className="mt-0.5 text-2xl font-bold text-tiilt-ink">
                {value}
            </div>
        </div>
    )
    return (
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
            {card("Sessions", all.length)}
            {card(
                "Live now",
                live > 0 ? (
                    <span className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-tiilt-danger" />
                        {live}
                    </span>
                ) : (
                    0
                ),
            )}
            {card("This week", thisWeek)}
        </div>
    )
}

const PODS_EXPLAINER =
    "A session is one recorded session. Each pod is a participant group (device) within that session — a session can have several pods running at once. Expand a session to see its pods, and click any pod to open its analysis."

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

// Folders are navigation, not content: one wrapping row of compact chips
// instead of a full-width row per folder.
function FolderChip({ folder, count, onOpen, openFolderDialog }) {
    return (
        <span className="flex items-center gap-0.5 rounded-full border border-tiilt-line bg-white py-1 pr-1 pl-3 transition hover:border-tiilt">
            <button
                onClick={() => onOpen(folder.id)}
                className="flex min-w-0 cursor-pointer items-center gap-1.5 text-sm font-semibold text-tiilt-ink transition hover:text-tiilt"
            >
                <span className="flex-none text-tiilt">
                    <FolderIcon className="h-4 w-4" />
                </span>
                <span className="max-w-40 truncate">{folder.name}</span>
                {count != null ? (
                    <span className="font-normal text-tiilt-muted">
                        {count}
                    </span>
                ) : null}
            </button>
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
        </span>
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
                                {pod.analysis_running ? (
                                    <StatusPill tone="orange" pulse>
                                        Analyzing…
                                    </StatusPill>
                                ) : pod.posthoc_analyzed_date ? (
                                    <StatusPill tone="teal">
                                        Analyzed
                                    </StatusPill>
                                ) : null}
                                {pod.speaker_count > 0 ? (
                                    <span className="flex-none text-tiilt-muted">
                                        {pod.speaker_count}{" "}
                                        {pod.speaker_count === 1
                                            ? "participant"
                                            : "participants"}
                                    </span>
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

function SessionRow({ session, onOpen, openSessionDialog, endSession, checked, onToggle, renameInline, folderHint }) {
    const [expanded, setExpanded] = useState(false)
    const [editing, setEditing] = useState(false)
    const hasPods = session.pod_count != null && session.pod_count > 0
    const commitRename = (value) => {
        setEditing(false)
        if (renameInline) renameInline(session, value)
    }
    return (
        <>
            <tr
                onClick={() => onOpen(session)}
                title={`Open ${session.title}`}
                className="group cursor-pointer border-t border-tiilt-line bg-white transition first:border-t-0 hover:bg-tiilt-soft/50"
            >
                <td className="py-2 pr-1 pl-4">
                    <button
                        onClick={(e) => {
                            e.stopPropagation()
                            onToggle()
                        }}
                        role="checkbox"
                        aria-checked={!!checked}
                        aria-label={`Select session ${session.title}`}
                        title={
                            (session.has_video
                                ? "Video session"
                                : "Audio-only session") +
                            (checked
                                ? " — click to deselect"
                                : " — click to select for bulk actions")
                        }
                        className={
                            "flex h-9 w-9 flex-none cursor-pointer items-center justify-center rounded-md transition " +
                            (checked
                                ? "bg-tiilt text-white ring-2 ring-tiilt/40"
                                : session.recording
                                  ? "bg-tiilt-danger-soft text-tiilt-danger hover:ring-2 hover:ring-tiilt/30"
                                  : "bg-tiilt-soft text-tiilt hover:ring-2 hover:ring-tiilt/30")
                        }
                    >
                        {checked ? (
                            "\u2713"
                        ) : session.has_video ? (
                            <Camera />
                        ) : (
                            <svg width="20" height="20" viewBox="0 0 20 30">
                                <MicIcon fill="currentColor" />
                            </svg>
                        )}
                    </button>
                </td>
                <td className="max-w-0 px-3 py-2" style={{ width: "38%" }}>
                    {editing ? (
                        <input
                            autoFocus
                            defaultValue={session.title}
                            aria-label="Session name"
                            maxLength={64}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") commitRename(e.target.value)
                                if (e.key === "Escape") setEditing(false)
                            }}
                            onBlur={(e) => commitRename(e.target.value)}
                            className="w-full rounded-md border border-tiilt bg-white px-2 py-0.5 text-sm font-semibold text-tiilt-ink outline-none focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                        />
                    ) : (
                        <span className="flex min-w-0 items-center gap-1">
                            <span
                                title={session.title}
                                className="truncate font-semibold text-tiilt-ink"
                            >
                                {session.title}
                            </span>
                            {session.recording ? (
                                <StatusPill tone="danger" dot pulse className="text-xs">
                                    Live
                                </StatusPill>
                            ) : session.analysis_running ? (
                                <StatusPill
                                    tone="orange"
                                    pulse
                                    className="text-xs"
                                    title="A full analysis is running right now"
                                >
                                    Analyzing{"\u2026"}
                                </StatusPill>
                            ) : null}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    setEditing(true)
                                }}
                                aria-label={`Rename ${session.title}`}
                                title="Rename"
                                className="flex h-6 w-6 flex-none cursor-pointer items-center justify-center rounded text-xs text-tiilt-muted opacity-0 transition group-hover:opacity-100 hover:bg-tiilt-soft hover:text-tiilt focus-visible:opacity-100"
                            >
                                {"\u270E"}
                            </button>
                        </span>
                    )}
                    {folderHint ? (
                        <span
                            title={`In folder ${folderHint}`}
                            className="mt-0.5 flex w-fit flex-none items-center gap-1 rounded-full bg-tiilt-line/40 px-1.5 py-0.5 text-[11px] font-semibold whitespace-nowrap text-tiilt-muted"
                        >
                            <FolderIcon className="h-3 w-3" />
                            {folderHint}
                        </span>
                    ) : null}
                </td>
                <td className="px-3 py-2 whitespace-nowrap text-tiilt-ink">
                    {formatDate(session.creation_date)}
                </td>
                <td className="px-3 py-2 text-right font-ahamono text-xs tabular-nums whitespace-nowrap text-tiilt-ink">
                    {session.lengthFormatted}
                </td>
                <td className="px-3 py-2 text-right font-ahamono tabular-nums whitespace-nowrap text-tiilt-ink">
                    {session.participant_count > 0 ? (
                        session.participant_count
                    ) : (
                        <span className="text-tiilt-muted">{"\u2014"}</span>
                    )}
                </td>
                <td className="px-3 py-2 text-right font-ahamono tabular-nums whitespace-nowrap text-tiilt-ink">
                    {hasPods ? (
                        session.pod_count
                    ) : (
                        <span className="text-tiilt-muted">{"\u2014"}</span>
                    )}
                </td>
                <td
                    className="py-2 pr-3 pl-1 text-right whitespace-nowrap"
                    onClick={(e) => e.stopPropagation()}
                >
                    <span className="flex items-center justify-end gap-0.5">
                        {hasPods ? (
                            <button
                                onClick={() => setExpanded((v) => !v)}
                                title={expanded ? "Hide pods" : "Show pods"}
                                aria-expanded={expanded}
                                className="flex h-7 w-7 flex-none cursor-pointer items-center justify-center rounded-md text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
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
                    </span>
                </td>
            </tr>
            {expanded ? (
                <tr className="border-t border-tiilt-line bg-tiilt-ground/40">
                    <td colSpan={7} className="px-3 py-1">
                        <PodDurations sessionId={session.id} />
                    </td>
                </tr>
            ) : null}
        </>
    )
}

// Clickable, aria-sorted column header driving the shared sortBy state
// ("date-desc" style keys).
function SortableTh({ label, sortKey, sortBy, setSortBy, alignRight, defaultDir = "desc" }) {
    const active = sortBy.startsWith(sortKey + "-")
    const dir = active ? sortBy.slice(sortKey.length + 1) : null
    const next = active
        ? `${sortKey}-${dir === "asc" ? "desc" : "asc"}`
        : `${sortKey}-${defaultDir}`
    return (
        <th
            aria-sort={
                active ? (dir === "asc" ? "ascending" : "descending") : undefined
            }
            className={
                "sticky top-0 bg-tiilt-ground px-3 py-2.5 whitespace-nowrap " +
                (alignRight ? "text-right" : "text-left")
            }
        >
            <button
                onClick={() => setSortBy(next)}
                className="cursor-pointer text-sm font-semibold text-tiilt-ink transition hover:text-tiilt"
            >
                {label}
                <span
                    aria-hidden="true"
                    className={
                        "ml-1 inline-block text-[10px] " +
                        (active ? "text-tiilt" : "text-tiilt-line")
                    }
                >
                    {active && dir === "asc" ? "\u25B2" : "\u25BC"}
                </span>
            </button>
        </th>
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
                    <div className="mx-auto w-full max-w-4xl px-4 py-8">
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
                                <span
                                    tabIndex={0}
                                    role="note"
                                    title={PODS_EXPLAINER}
                                    aria-label={PODS_EXPLAINER}
                                    className="flex h-5 w-5 flex-none cursor-help items-center justify-center rounded-full bg-tiilt-line/40 text-[11px] font-bold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                                >
                                    ?
                                </span>
                            </nav>
                            <div className="flex flex-wrap justify-end gap-2">
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
                            <SessionStats sessions={props.sessions} />
                        ) : null}

                        {!props.isLoading ? (
                            <div className="mb-4 flex flex-wrap items-center gap-2">
                                {props.displayedFolders.map((folder, index) => (
                                    <FolderChip
                                        key={index}
                                        folder={folder}
                                        count={(props.sessions || []).filter((x) => x.folder === folder.id).length}
                                        onOpen={props.displayFolder}
                                        openFolderDialog={
                                            props.openFolderDialog
                                        }
                                    />
                                ))}
                                <button
                                    onClick={() => props.openFolderDialog("NewFolder")}
                                    className="flex cursor-pointer items-center gap-1.5 rounded-full border border-dashed border-tiilt-line px-3 py-1.5 text-sm font-semibold text-tiilt-muted transition hover:border-tiilt hover:text-tiilt"
                                >
                                    <span aria-hidden="true">+</span>
                                    New folder
                                </button>
                            </div>
                        ) : null}

                        {!props.isLoading &&
                        (props.videoCount + props.audioCount > 0 ||
                            props.searchingAll) ? (
                            <div className="mt-4">
                                <SortControl
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
                                    <div className="overflow-x-auto rounded-xl border border-tiilt-line bg-white">
                                        <table className="w-full border-collapse text-left text-sm">
                                            <thead>
                                                <tr className="border-b border-tiilt-line">
                                                    <SortableTh
                                                        label="Type"
                                                        sortKey="type"
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <SortableTh
                                                        label="Session"
                                                        sortKey="name"
                                                        defaultDir="asc"
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <SortableTh
                                                        label="Date"
                                                        sortKey="date"
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <SortableTh
                                                        label="Duration"
                                                        sortKey="length"
                                                        alignRight
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <SortableTh
                                                        label="People"
                                                        sortKey="participants"
                                                        alignRight
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <SortableTh
                                                        label="Pods"
                                                        sortKey="pods"
                                                        alignRight
                                                        sortBy={props.sortBy}
                                                        setSortBy={props.setSortBy}
                                                    />
                                                    <th className="sticky top-0 bg-tiilt-ground py-2.5 pr-3 pl-1">
                                                        <span className="sr-only">
                                                            Actions
                                                        </span>
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {props.displayedSessions.map(
                                                    (session) => (
                                                        <SessionRow
                                                            key={session.id}
                                                            session={session}
                                                            checked={props.selectedIds[session.id]}
                                                            onToggle={() => props.toggleSelected(session.id)}
                                                            onOpen={props.goToSession}
                                                            renameInline={props.renameSessionInline}
                                                            folderHint={
                                                                props.searchingAll
                                                                    ? (props.folders.find((f) => f.id === session.folder) || {}).name || "Home"
                                                                    : null
                                                            }
                                                            openSessionDialog={
                                                                props.openSessionDialog
                                                            }
                                                            endSession={
                                                                props.endSession
                                                            }
                                                        />
                                                    ),
                                                )}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="py-8 text-center text-sm text-tiilt-muted">
                                        {props.searchingAll
                                            ? "No sessions match your search (searched every folder)."
                                            : props.videoFilter === "video"
                                              ? "No sessions with video."
                                              : "No audio-only sessions."}
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
