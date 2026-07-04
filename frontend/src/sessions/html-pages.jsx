import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { DialogBox, GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component"
import style from "./sessions.module.css"
import style2 from "../components/context-menu/context-menu.module.css"
import breadcrumbIcon from "../assets/img/icon-back.svg"
import FolderIcon from "../Icons/Folder"
import MicIcon from "../Icons/Mic"
import { AppSpinner } from "../spinner/spinner-component"

const rowClass =
    "group flex items-center gap-2.5 rounded-lg border border-tiilt-line bg-white px-3 py-2 transition hover:border-tiilt hover:shadow-[0_8px_20px_-16px_rgba(42,23,74,0.5)]"
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
                    ? "bg-white text-tiilt shadow-[0_1px_3px_-1px_rgba(42,23,74,0.35)]"
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
}) {
    return (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
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

function FolderRow({ folder, onOpen, openFolderDialog }) {
    return (
        <li className={rowClass}>
            <span className="flex h-9 w-9 flex-none items-center justify-center rounded-md bg-tiilt-soft text-tiilt">
                <FolderIcon />
            </span>
            <button
                onClick={() => onOpen(folder.id)}
                className="min-w-0 grow cursor-pointer truncate text-left text-base font-semibold text-tiilt-ink"
            >
                {folder.name}
            </button>
            <div className="flex-none">
                <AppContextMenu>
                    <div
                        className={menuItemClass}
                        onClick={() => openFolderDialog("RenameFolder", folder)}
                    >
                        Edit Name
                    </div>
                    <div
                        className={menuItemClass}
                        onClick={() => openFolderDialog("MoveFolder", folder)}
                    >
                        Move To...
                    </div>
                    <div
                        className={menuDangerClass}
                        onClick={() => openFolderDialog("DeleteFolder", folder)}
                    >
                        Delete
                    </div>
                </AppContextMenu>
            </div>
        </li>
    )
}

function SessionRow({ session, onOpen, openSessionDialog, endSession }) {
    return (
        <li className={rowClass}>
            <span
                className={
                    "flex h-9 w-9 flex-none items-center justify-center rounded-md " +
                    (session.recording
                        ? "bg-tiilt-danger-soft text-tiilt-danger"
                        : "bg-tiilt-soft text-tiilt")
                }
            >
                <svg width="20" height="20" viewBox="0 0 20 30">
                    <MicIcon fill="currentColor" />
                </svg>
            </span>
            <button
                onClick={() => onOpen(session)}
                className="flex min-w-0 grow cursor-pointer flex-col text-left"
            >
                <span className="truncate text-base font-semibold text-tiilt-ink">
                    {session.title}
                </span>
                <span className="mt-0.5 flex items-center gap-2 text-xs text-tiilt-muted">
                    {session.creation_date.toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                    })}
                    <span aria-hidden="true">·</span>
                    <span className="font-ahamono tabular-nums">
                        {session.lengthFormatted}
                    </span>
                    {session.has_video ? (
                        <span
                            title="Video recorded for this session"
                            className="flex items-center gap-1 rounded-full bg-tiilt-soft px-1.5 py-0.5 font-semibold text-tiilt"
                        >
                            <svg
                                width="12"
                                height="12"
                                viewBox="0 0 24 24"
                                fill="none"
                                aria-hidden="true"
                            >
                                <rect
                                    x="2.5"
                                    y="6"
                                    width="12"
                                    height="12"
                                    rx="2.5"
                                    fill="currentColor"
                                />
                                <path
                                    d="M16 10l5-3v10l-5-3z"
                                    fill="currentColor"
                                />
                            </svg>
                            Video
                        </span>
                    ) : null}
                </span>
            </button>
            {session.recording ? (
                <span className="flex flex-none items-center gap-1.5 rounded-full bg-tiilt-danger-soft px-2.5 py-1 text-xs font-semibold text-tiilt-danger">
                    <span className="h-1.5 w-1.5 rounded-full bg-tiilt-danger" />
                    Live
                </span>
            ) : null}
            <div className="flex-none">
                <AppContextMenu>
                    <div
                        className={menuItemClass}
                        onClick={() =>
                            openSessionDialog("RenameSession", session)
                        }
                    >
                        Edit Name
                    </div>
                    <div
                        className={menuItemClass}
                        onClick={() =>
                            openSessionDialog("MoveSession", session)
                        }
                    >
                        Move To...
                    </div>
                    {!session.recording ? (
                        <div
                            className={menuDangerClass}
                            onClick={() =>
                                openSessionDialog("DeleteSession", session)
                            }
                        >
                            Delete
                        </div>
                    ) : (
                        <div
                            className={menuDangerClass}
                            onClick={() => endSession(session)}
                        >
                            End
                        </div>
                    )}
                </AppContextMenu>
            </div>
        </li>
    )
}

function DiscussionSessionPage(props) {
    return (
        <>
            <div className="main-container">
                <Appheader
                    title={"Manage Discussions"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigateToHomescreen}
                />

                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-3xl px-4 py-8">
                        {props.isLoading ? (
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <div className={style["load-text"]}>
                                    Loading...
                                </div>
                                <AppSpinner />
                            </div>
                        ) : (
                            <></>
                        )}
                        {!props.isLoading &&
                        props.sessions.length === 0 &&
                        props.folders.length === 0 ? (
                            <div className={style["empty-session-list"]}>
                                <div className={style["load-text"]}>
                                    {" "}
                                    No Discussions or Folders{" "}
                                </div>
                                <div className={style["load-text-description"]}>
                                    {" "}
                                    Tap the buttons below to record your first
                                    discussion or create your first folder.{" "}
                                </div>
                            </div>
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
                                        <img
                                            alt=""
                                            src={breadcrumbIcon}
                                            className="h-4 w-4"
                                        />
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
                            <div className="flex flex-none gap-2">
                                <button
                                    className="rounded-lg border border-tiilt-line bg-white px-4 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"
                                    onClick={() =>
                                        props.openFolderDialog("NewFolder")
                                    }
                                >
                                    New folder
                                </button>
                                <button
                                    className="rounded-lg bg-tiilt px-4 py-2 text-sm font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
                                    onClick={props.newRecording}
                                >
                                    New discussion
                                </button>
                            </div>
                        </div>

                        {!props.isLoading &&
                        props.displayedFolders.length > 0 ? (
                            <ul className="flex flex-col gap-1.5">
                                {props.displayedFolders.map((folder, index) => (
                                    <FolderRow
                                        key={index}
                                        folder={folder}
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
                                    count={props.videoCount + props.audioCount}
                                    videoFilter={props.videoFilter}
                                    setVideoFilter={props.setVideoFilter}
                                    videoCount={props.videoCount}
                                    audioCount={props.audioCount}
                                />
                                {props.displayedSessions.length > 0 ? (
                                    <ul className="flex flex-col gap-1.5">
                                        {props.displayedSessions.map(
                                            (session, index) => (
                                                <SessionRow
                                                    key={index}
                                                    session={session}
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
                                            ? "discussions with video"
                                            : "audio-only discussions"}
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
                                    <div>
                                        <div className={style["folder-empty"]}>
                                            {" "}
                                            Folder Empty{" "}
                                        </div>
                                    </div>
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

            <GenericDialogBox show={props.currentForm !== ""}>
                {props.currentForm === "RenameSession" ? (
                    <div
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
                            Update Discussion Name:
                        </div>
                        <input
                            id="txtName"
                            defaultValue={props.selectedSession.title}
                            className={style["field-input"]}
                            maxLength="64"
                        />
                        <div>
                            {props.invalidName
                                ? "Your proposed rename is invalid."
                                : ""}
                        </div>
                        <button
                            className={style["basic-button"]}
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
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
                            Update Folder Name:
                        </div>
                        <input
                            id="txtName"
                            defaultValue={props.selectedFolder.name}
                            className={style["field-input"]}
                            maxLength="64"
                        />
                        <div>
                            {props.invalidName
                                ? "Your proposed rename is invalid."
                                : ""}
                        </div>
                        <button
                            className={style["basic-button"]}
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
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
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
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
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
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
                            {" "}
                            Add New Folder
                        </div>
                        <input
                            placeholder="Enter new file name"
                            id="txtName"
                            className={style["field-input"]}
                            maxLength="64"
                        />
                        {!props.breadcrumbs.length > 0 ? (
                            <div
                                className={style["basic-button"]}
                                onClick={() =>
                                    props.addFolder(
                                        document.getElementById("txtName")
                                            .value,
                                        null,
                                    )
                                }
                            >
                                {" "}
                                Confirm
                            </div>
                        ) : (
                            <div
                                className={style["basic-button"]}
                                onClick={() =>
                                    props.addFolder(
                                        document.getElementById("txtName")
                                            .value,
                                        props.breadcrumbs[
                                            props.breadcrumbs.length - 1
                                        ].id,
                                    )
                                }
                            >
                                {" "}
                                Confirm
                            </div>
                        )}

                        <button
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
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
                                className={style["basic-button"]}
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
                            className={style["cancel-button"]}
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
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
                            Move Discussion
                        </div>
                        <AppFolderSelectComponent
                            selectableFolders={props.selectableFolders}
                            setFolderSelect={props.setFolderSelect}
                            breadcrumbs={props.breadcrumbs}
                        />
                        {/* <app-folder-select #folderSelect [folders] = "selectableFolders" ></app - folder - select > */}
                        {props.folderSelect !== null ? (
                            <button
                                className={style["basic-button"]}
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
                            className={style["cancel-button"]}
                            onClick={props.closeDialog}
                        >
                            {" "}
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "Loading" ? (
                    <div
                        className={style["dialog-window"]}
                        style={{ minWidth: "min(20rem, 90vw)" }}
                    >
                        <div className={style["dialog-heading"]}>
                            Loading...please wait...
                        </div>
                    </div>
                ) : (
                    <></>
                )}
            </GenericDialogBox>

            <DialogBox
                itsclass={"add-dialog"}
                heading={"Error"}
                message={props.alertMessage}
                show={props.showAlert}
                closedialog={props.closeAlert}
            />
        </>
    )
}

export { DiscussionSessionPage }
