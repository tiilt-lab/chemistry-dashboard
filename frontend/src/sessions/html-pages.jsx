import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { DialogBox, GenericDialogBox } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component"
import style from "./sessions.module.css"
import style2 from "../components/context-menu/context-menu.module.css"
import breadcrumbIcon from "../assets/img/icon-back.svg"
import FolderIcon from "../Icons/Folder"
import MicIcon from "../Icons/Mic"
import { adjDim } from "../myhooks/custom-hooks"
import { AppSpinner } from "../spinner/spinner-component"

function DiscussionSessionPage(props) {
    return (
        <>
            <div className="main-container items-center">
                <Appheader
                    title={"Manage Discussions"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigateToHomescreen}
                />

                <div
                    className={style["list-container"]}
                    style={{ "maxWidth": adjDim(375) + "px" }}
                >
                    {props.isLoading ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <div className={style["load-text"]}>Loading...</div>
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

                    <div className={style["breadcrumb-container"]}>
                        {props.breadcrumbs.length > 0 ? (
                            <div onClick={props.goBackToPrevious}>
                                <img
                                    alt="breadcumbs"
                                    src={breadcrumbIcon}
                                    className={style["breadcrumb-arrow-icon"]}
                                />
                            </div>
                        ) : (
                            <></>
                        )}
                        {props.folders.length > 0 ? (
                            <>
                                <span
                                    onClick={props.goBackToPrevious}
                                    className={style["crumb-name"]}
                                    style={{ "maxWidth": adjDim(240) + "px" }}
                                >
                                    {" "}
                                    Home
                                </span>
                                {props.breadcrumbs.length > 1 ? (
                                    <span
                                        className={style.breadcrumbs}
                                        style={{ cursor: "default" }}
                                    >
                                        {" "}
                                        / . . . /{" "}
                                    </span>
                                ) : (
                                    <></>
                                )}
                                {props.breadcrumbs.length === 1 ? (
                                    <span className={style["breadcrumbs"]}>
                                        {" "}
                                        /{" "}
                                    </span>
                                ) : (
                                    <></>
                                )}
                                {props.breadcrumbs.length > 0 ? (
                                    <div
                                        className={style["crumb-name"]}
                                        style={{
                                            "maxWidth": adjDim(240) + "px",
                                            cursor: "default",
                                        }}
                                    >
                                        {" "}
                                        {
                                            props.breadcrumbs[
                                                props.breadcrumbs.length - 1
                                            ].name
                                        }
                                    </div>
                                ) : (
                                    <></>
                                )}
                            </>
                        ) : (
                            <></>
                        )}
                    </div>

                    {!props.isLoading && props.displayedFolders.length > 0 ? (
                        <div>
                            <ul className={style.list}>
                                {props.displayedFolders.map((folder, index) => (
                                    <li
                                        key={index}
                                        className={style["folder-item"]}
                                    >
                                        <div
                                            alt="folder"
                                            className={style["folder-icon"]}
                                        >
                                            <FolderIcon/>
                                        </div>
                                        <div
                                            className={style["folder-title"]}
                                            onClick={() => {
                                                props.displayFolder(folder.id)
                                            }}
                                        >
                                            {folder.name}
                                        </div>
                                        <div
                                            className={style["folder-options"]}
                                        >
                                            <AppContextMenu>
                                                <div
                                                    className={
                                                        style2["menu-item"]
                                                    }
                                                    onClick={() => {
                                                        props.openFolderDialog(
                                                            "RenameFolder",
                                                            folder,
                                                        )
                                                    }}
                                                >
                                                    Edit Name
                                                </div>
                                                <div
                                                    className={
                                                        style2["menu-item"]
                                                    }
                                                    onClick={() => {
                                                        props.openFolderDialog(
                                                            "MoveFolder",
                                                            folder,
                                                        )
                                                    }}
                                                >
                                                    {" "}
                                                    Move To...
                                                </div>
                                                <div
                                                    className={`${style2["menu-item"]} ${style2["red"]}`}
                                                    onClick={() => {
                                                        props.openFolderDialog(
                                                            "DeleteFolder",
                                                            folder,
                                                        )
                                                    }}
                                                >
                                                    {" "}
                                                    Delete
                                                </div>
                                            </AppContextMenu>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ) : (
                        <></>
                    )}

                    {!props.isLoading && props.displayedSessions.length > 0 ? (
                        <div>
                            <ul className={style.list}>
                                {props.displayedSessions.map(
                                    (session, index) => (
                                        <li
                                            key={index}
                                            className={style["session-item"]}
                                        >
                                            <svg
                                                x="0"
                                                y="0"
                                                with={adjDim(24) + ""}
                                                height={adjDim(24) + ""}
                                                viewBox="0 0 20 30"
                                                className="m-2"
                                            >
                                                <MicIcon
                                                    fill={
                                                        session.recording
                                                            ? "#FF6363"
                                                            : "#7878FA"
                                                    }
                                                ></MicIcon>
                                            </svg>
                                            <div
                                                className={style["click-mask"]}
                                                style={{
                                                    width: adjDim(310) + "px",
                                                }}
                                                onClick={() => {
                                                    props.goToSession(session)
                                                }}
                                            ></div>
                                            <div
                                                className={
                                                    style["session-title"]
                                                }
                                            >
                                                {session.title}
                                            </div>
                                            <div
                                                className={
                                                    style["session-date"]
                                                }
                                            >
                                                {session.formattedDate}
                                            </div>
                                            <div
                                                className="m-2"
                                            >
                                                <AppContextMenu>
                                                    <div
                                                        className={
                                                            style2["menu-item"]
                                                        }
                                                        onClick={() => {
                                                            props.openSessionDialog(
                                                                "RenameSession",
                                                                session,
                                                            )
                                                        }}
                                                    >
                                                        Edit Name
                                                    </div>
                                                    <div
                                                        className={
                                                            style2["menu-item"]
                                                        }
                                                        onClick={() => {
                                                            props.openSessionDialog(
                                                                "MoveSession",
                                                                session,
                                                            )
                                                        }}
                                                    >
                                                        {" "}
                                                        Move To...
                                                    </div>
                                                    {!session.recording ? (
                                                        <div
                                                            className={`${style2["menu-item"]} ${style2["red"]}`}
                                                            onClick={() => {
                                                                props.openSessionDialog(
                                                                    "DeleteSession",
                                                                    session,
                                                                )
                                                            }}
                                                        >
                                                            {" "}
                                                            Delete
                                                        </div>
                                                    ) : (
                                                        <></>
                                                    )}
                                                    {session.recording ? (
                                                        <div
                                                            className={`${style2["menu-item"]} ${style2["red"]}`}
                                                            onClick={() => {
                                                                props.endSession(
                                                                    session,
                                                                )
                                                            }}
                                                        >
                                                            {" "}
                                                            End
                                                        </div>
                                                    ) : (
                                                        <></>
                                                    )}
                                                </AppContextMenu>
                                            </div>
                                            <div
                                                className={
                                                    style["session-title"]
                                                }
                                            >
                                                {session.name}
                                            </div>
                                        </li>
                                    ),
                                )}
                            </ul>
                        </div>
                    ) : (
                        <></>
                    )}

                    {(props.folders.length > 0 || props.sessions.length > 0) && !props.isLoading? (
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
                <button
                    className={`${style["basic-button"]} ${style["medium-button"]}`}
                    onClick={() => props.openFolderDialog("NewFolder")}
                    style={{ width: adjDim(374) + "px" }}
                >
                    New Folder
                </button>
                <button
                    className={`${style["basic-button"]} ${style["medium-button"]}`}
                    onClick={props.newRecording}
                    style={{ width: adjDim(374) + "px" }}
                >
                    New Discussion
                </button>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
                {props.currentForm === "RenameSession" ? (
                    <div
                        className={style["dialog-window"]}
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
                        style={{ "min-width": adjDim(270) + "px" }}
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
