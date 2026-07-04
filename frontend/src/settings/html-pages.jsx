import style from "./settings.module.css"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"

const SECTIONS = [
    {
        title: "Account",
        show: () => true,
        items: [{ label: "Change Password", dialog: ["ChangePassword"] }],
    },
    {
        title: "Manage Accounts",
        show: (u) => u.isAdmin || u.isSuper,
        items: [
            { label: "View Users", dialog: ["ViewUsers", true] },
            { label: "Add User", dialog: ["AddUser"] },
            {
                label: "Delete User",
                dialog: ["DeleteUser", true],
                danger: true,
            },
            { label: "Change User Role", dialog: ["UserRole", true] },
            { label: "Lock User", dialog: ["LockUser", true] },
            { label: "Unlock User", dialog: ["UnlockUser", true] },
            { label: "Reset User Password", dialog: ["ResetUser", true] },
        ],
    },
    {
        title: "Manage Student Profiles",
        show: (u) => u.isAdmin || u.isSuper,
        items: [
            { label: "View Students", dialog: ["ViewStudentProfile", true] },
            { label: "Add Student Profile", dialog: ["AddStudentProfile"] },
            {
                label: "Delete Student Profile",
                dialog: ["DeleteStudentProfile", true],
                danger: true,
            },
            {
                label: "Sync Student Profiles",
                dialog: ["SyncStudentProfile", true],
            },
        ],
    },
    {
        title: "Manage Raters",
        show: (u) => u.isAdmin || u.isSuper,
        items: [
            { label: "View Raters", dialog: ["ViewRaters", true] },
            { label: "Add Rater", dialog: ["AddRater"] },
            {
                label: "Delete Rater",
                dialog: ["DeleteRater", true],
                danger: true,
            },
        ],
    },
    {
        title: "Manage Server",
        show: (u) => u.isSuper,
        items: [
            { label: "Download Server Logs", dialog: ["ServerLogs"] },
            {
                label: "Download Device Logs",
                dialog: ["DeviceLogs", false, true],
            },
            {
                label: "Clear Server Logs",
                dialog: ["DeleteServerLogs"],
                danger: true,
            },
            {
                label: "Clear Device Logs",
                dialog: ["DeleteDeviceLogs", false, true],
                danger: true,
            },
            { label: "Allow API Access", dialog: ["AllowAPI", true] },
            {
                label: "Revoke API Access",
                dialog: ["RevokeAPI", true],
                danger: true,
            },
        ],
    },
]

function OptionButton({ label, danger, onClick }) {
    return (
        <button
            onClick={onClick}
            className={
                "flex h-12 items-center justify-between rounded-xl border bg-white px-4 text-left text-sm font-semibold transition active:translate-y-px " +
                (danger
                    ? "border-tiilt-line text-tiilt-danger hover:border-tiilt-danger hover:bg-tiilt-danger-soft"
                    : "border-tiilt-line text-tiilt-ink hover:border-tiilt hover:bg-tiilt-soft")
            }
        >
            {label}
            <span aria-hidden="true" className="text-tiilt-muted">
                ›
            </span>
        </button>
    )
}

function SettingComponentPage(props) {
    return (
        <>
            <div className="main-container">
                <Appheader
                    title={"Settings"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={props.navigateToHomescreen}
                />
                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-8">
                        {SECTIONS.filter((s) => s.show(props.user)).map(
                            (section) => (
                                <section
                                    key={section.title}
                                    className="flex flex-col gap-3"
                                >
                                    <h2 className="text-xs font-semibold tracking-wider text-tiilt-muted uppercase">
                                        {section.title}
                                    </h2>
                                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                        {section.items.map((item) => (
                                            <OptionButton
                                                key={item.label}
                                                label={item.label}
                                                danger={item.danger}
                                                onClick={() =>
                                                    props.openDialog(
                                                        ...item.dialog,
                                                    )
                                                }
                                            />
                                        ))}
                                    </div>
                                </section>
                            ),
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox show={props.currentForm !== ""}>
                {props.currentForm === "ChangePassword" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Change Password
                        </div>
                        <div className={style["input-header"]}>
                            Current password
                        </div>
                        <input
                            id="txtCurrent"
                            className={style["field-input"]}
                            type="password"
                        />
                        <div className={style["input-header"]}>
                            New password
                        </div>
                        <input
                            id="txtNew"
                            className={style["field-input"]}
                            type="password"
                        />
                        <div className={style["input-header"]}>
                            Confirm new password
                        </div>
                        <input
                            id="txtConfirm"
                            className={style["field-input"]}
                            type="password"
                        />
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.changePassword(
                                    document.getElementById("txtCurrent").value,
                                    document.getElementById("txtNew").value,
                                    document.getElementById("txtConfirm").value,
                                )
                            }
                        >
                            Change Password
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

                {props.currentForm === "ViewUsers" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            View Users
                        </div>
                        <div className={style["user-table"]}>
                            <div className={style["user-row"]}>
                                <span className={style["user-name bold"]}>
                                    Username / Email
                                </span>
                                <span className={style["user-role bold"]}>
                                    Role
                                </span>
                                <span className={style["user-locked bold"]}>
                                    Locked
                                </span>
                                <span className={style["user-api bold"]}>
                                    API
                                </span>
                            </div>
                            {props.users.map((u, index) => (
                                <div key={index} className={style["user-row"]}>
                                    <span className={style["user-name"]}>
                                        {u.email}
                                    </span>
                                    <span className={style["user-role"]}>
                                        {u.role}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {JSON.stringify(u.locked)}
                                    </span>
                                    <span className={style["user-api"]}>
                                        {JSON.stringify(u.api_access)}
                                    </span>
                                </div>
                            ))}
                        </div>
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

                {props.currentForm === "ViewStudentProfile" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            View Students
                        </div>
                        <div className={style["user-table"]}>
                            <div className={style["user-row"]}>
                                <span className={style["user-name bold"]}>
                                    Username
                                </span>
                                <span className={style["user-role bold"]}>
                                    First Name
                                </span>
                                <span className={style["user-locked bold"]}>
                                    Last Name
                                </span>
                            </div>
                            {props.students.map((s, index) => (
                                <div key={index} className={style["user-row"]}>
                                    <span className={style["user-name"]}>
                                        {s.username}
                                    </span>
                                    <span className={style["user-role"]}>
                                        {s.lastname}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {s.firstname}
                                    </span>
                                </div>
                            ))}
                        </div>
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

                {props.currentForm === "ViewRaters" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            View Raters
                        </div>
                        <div className={style["user-table"]}>
                            <div className={style["user-row"]}>
                                <span className={style["user-name bold"]}>
                                    rater_id
                                </span>
                                <span className={style["user-role bold"]}>
                                    sess_id
                                </span>
                                <span className={style["user-locked bold"]}>
                                    dev_id
                                </span>
                                <span className={style["user-locked bold"]}>
                                    spkr_id
                                </span>
                                <span className={style["user-locked bold"]}>
                                    spkr_Tag
                                </span>
                                <span className={style["user-locked bold"]}>
                                    type
                                </span>
                            </div>
                            {props.raters.map((r, index) => (
                                <div key={index} className={style["user-row"]}>
                                    <span className={style["user-name"]}>
                                        {r.raterid}
                                    </span>
                                    <span className={style["user-role"]}>
                                        {r.sessionid}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {r.sessiondeviceid}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {r.speakerid}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {r.speakertag}
                                    </span>
                                    <span className={style["user-locked"]}>
                                        {r.dashboardtype}
                                    </span>
                                </div>
                            ))}
                        </div>
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

                {props.currentForm === "AddUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>Add User</div>
                        <div className={style["input-header"]}>Email</div>
                        <input
                            id="txtName"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>Role</div>
                        <select id="ddRole" className={style["dropdown-input"]}>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.createUser(
                                    document.getElementById("txtName").value,
                                    document.getElementById("ddRole").value,
                                )
                            }
                        >
                            Create User
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

                {props.currentForm === "AddRater" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>Add Rater</div>
                        <div className={style["input-header"]}>Session ID</div>
                        <input
                            id="sessionId"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>
                            Session Device ID
                        </div>
                        <input
                            id="sessionDeviceId"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>Speaker ID</div>
                        <input
                            id="speakerId"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>Speaker Tag</div>
                        <input
                            id="speakertag"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>Rater ID</div>
                        <input
                            id="raterId"
                            className={style["field-input"]}
                            type="text"
                        />
                        <div className={style["input-header"]}>
                            Dashboard Type
                        </div>
                        <select id="type" className={style["dropdown-input"]}>
                            <option value="quantitative">
                                Quantitative Dashboard
                            </option>
                            <option value="reflection">
                                Reflection Dashboard
                            </option>
                        </select>
                        <select
                            id="evaluationcategory"
                            className={style["dropdown-input"]}
                        >
                            <option value="visualization">Visualization</option>
                            <option value="reflection">Reflection</option>
                            <option value="multimodal">Multimodal</option>
                            <option value="unimodal">Unimodal </option>
                            <option value="structured">Structured</option>
                            <option value="unstructured">Unstructured </option>
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.createRater(
                                    document.getElementById("sessionId").value,
                                    document.getElementById("sessionDeviceId")
                                        .value,
                                    document.getElementById("speakerId").value,
                                    document.getElementById("speakertag").value,
                                    document.getElementById("raterId").value,
                                    document.getElementById("type").value,
                                    document.getElementById(
                                        "evaluationcategory",
                                    ).value,
                                )
                            }
                        >
                            Create Rater
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

                {props.currentForm === "DeleteUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Delete User
                        </div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>

                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.confirmDeleteUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Delete User
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
                {props.currentForm === "DeleteStudentProfile" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Delete Student
                        </div>
                        <div className={style["input-header"]}>
                            Select Student
                        </div>
                        <select
                            id="ddStudent"
                            className={style["dropdown-input"]}
                        >
                            {props.students.map((s, index) => (
                                <option key={index} value={s.id}>
                                    {s.username}
                                </option>
                            ))}
                        </select>

                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.confirmDeleteStudent(
                                    document.getElementById("ddStudent").value,
                                )
                            }
                        >
                            Delete Student
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

                {props.currentForm === "DeleteRater" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Delete Rater
                        </div>
                        <div className={style["input-header"]}>
                            Select Rater
                        </div>
                        <select
                            id="ddRater"
                            className={style["dropdown-input"]}
                        >
                            {props.raters.map((s, index) => (
                                <option key={index} value={s.id}>
                                    {s.raterid +
                                        " " +
                                        s.sessionid +
                                        " " +
                                        s.sessiondeviceid +
                                        " " +
                                        s.speakertag +
                                        " " +
                                        s.dashboardtype}
                                </option>
                            ))}
                        </select>

                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.confirmDeleteRater(
                                    document.getElementById("ddRater").value,
                                )
                            }
                        >
                            Delete Rater
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

                {props.currentForm === "ConfirmDeleteUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Are you sure you want to delete{" "}
                            {props.userToDelete.email}?
                        </div>
                        <button
                            className={style["basic-button"]}
                            onClick={props.deleteSelectedUser}
                        >
                            Delete User
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

                {props.currentForm === "ConfirmDeleteStudent" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Are you sure you want to delete{" "}
                            {props.studentToDelete.username}?
                        </div>
                        <button
                            className={style["basic-button"]}
                            onClick={props.deleteSelectedStudent}
                        >
                            Delete Student
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
                {props.currentForm === "ConfirmDeleteRater" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Are you sure you want to delete{" "}
                            {props.raterToDelete.raterid +
                                " for " +
                                props.raterToDelete.sessionid +
                                " " +
                                props.raterToDelete.sessiondeviceid +
                                " " +
                                props.raterToDelete.speakertag +
                                " " +
                                props.raterToDelete.dashboardtype}
                            ?
                        </div>
                        <button
                            className={style["basic-button"]}
                            onClick={props.deleteSelectedRater}
                        >
                            Delete Rater
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
                {props.currentForm === "LockUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>Lock User</div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.lockUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Lock User
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

                {props.currentForm === "UnlockUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Unlock User
                        </div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.unlockUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Unlock User
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
                {props.currentForm === "UserRole" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Change Role
                        </div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        <div className={style["input-header"]}>Select role</div>
                        <select id="ddRole" className={style["dropdown-input"]}>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.changeUserRole(
                                    document.getElementById("ddUser").value,
                                    document.getElementById("ddRole").value,
                                )
                            }
                        >
                            Change Role
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

                {props.currentForm === "ResetUser" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Reset User Password
                        </div>
                        <div className={style["input-header"]}>User</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.resetUserPassword(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Reset Password
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

                {props.currentForm === "ServerLogs" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Download Server Logs
                        </div>
                        <div className={style["input-header"]}>
                            Select service
                        </div>
                        <select
                            id="ddService"
                            className={style["dropdown-input"]}
                        >
                            <option value="dcs">
                                Discussion Capture Server
                            </option>
                            <option value="aps">
                                Audio Processing Service
                            </option>
                        </select>
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.downloadServerLogs(
                                    document.getElementById("ddService").value,
                                )
                            }
                        >
                            Download logs
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

                {props.currentForm === "DeviceLogs" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Download Device Logs
                        </div>
                        <div className={style["input-header"]}>
                            Select device
                        </div>
                        <select
                            id="ddDevice"
                            className={style["dropdown-input"]}
                        >
                            {props.devices.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.name}
                                </option>
                            ))}
                        </select>
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.downloadDeviceLogs(
                                    document.getElementById("ddDevice").value,
                                )
                            }
                        >
                            Download logs
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

                {props.currentForm === "DeleteServerLogs" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Clear Server Logs
                        </div>
                        <div className={style["input-header"]}>
                            Select service
                        </div>
                        <select
                            id="ddService"
                            className={style["dropdown-input"]}
                        >
                            <option value="dcs">
                                Discussion Capture Server
                            </option>
                            <option value="aps">
                                Audio Processing Service
                            </option>
                        </select>
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.deleteServerLogs(
                                    document.getElementById("ddService").value,
                                )
                            }
                        >
                            Clear logs
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

                {props.currentForm === "DeleteDeviceLogs" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Clear Device Logs
                        </div>
                        <div className={style["input-header"]}>
                            Select device
                        </div>
                        <select
                            id="ddDevice"
                            className={style["dropdown-input"]}
                        >
                            {props.devices.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.name}
                                </option>
                            ))}
                        </select>
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.deleteDeviceLogs(
                                    document.getElementById("ddDevice").value,
                                )
                            }
                        >
                            Clear logs
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

                {props.currentForm === "AllowAPI" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Allow API Access
                        </div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.allowAPIAccess(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Allow
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

                {props.currentForm === "RevokeAPI" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Revoke API Access
                        </div>
                        <div className={style["input-header"]}>Select user</div>
                        <select id="ddUser" className={style["dropdown-input"]}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={style["error-status"]}>
                                {props.status}
                            </div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={style["basic-button"]}
                            onClick={() =>
                                props.revokeAPIAccess(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Revoke
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

                {props.currentForm === "Loading" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            Loading...please wait...
                        </div>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "Status" ? (
                    <div className={style["add-dialog"]}>
                        <div className={style["dialog-heading"]}>
                            {props.statusTitle}
                        </div>
                        <div>{props.status}</div>
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
            </GenericDialogBox>
        </>
    )
}

export { SettingComponentPage }
