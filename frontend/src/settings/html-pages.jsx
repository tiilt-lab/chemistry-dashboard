import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { DataTable } from "../components/data-table"

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

const dlgHeading = "mb-3 text-lg font-semibold text-tiilt-ink"
const dlgClose =
    "mt-4 w-full rounded-lg border border-tiilt-line bg-white py-2.5 text-sm font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"
const dlgBody = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
const dlgLabel = "text-sm font-semibold text-tiilt-ink"
const dlgInput =
    "h-11 w-full rounded-lg border border-tiilt-line bg-white px-3 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
const dlgSelect =
    "h-11 w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 pr-8 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
const dlgPrimary =
    "mt-2 h-11 rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
const dlgCancel =
    "h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"
const dlgError =
    "rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger"
const dlgDanger =
    "mt-2 h-11 rounded-lg bg-tiilt-danger font-semibold text-white transition hover:brightness-90 active:translate-y-px"

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
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Change Password</div>
                        <div className={dlgLabel}>Current password</div>
                        <input
                            id="txtCurrent"
                            className={dlgInput}
                            type="password"
                        />
                        <div className={dlgLabel}>New password</div>
                        <input
                            id="txtNew"
                            className={dlgInput}
                            type="password"
                        />
                        <div className={dlgLabel}>Confirm new password</div>
                        <input
                            id="txtConfirm"
                            className={dlgInput}
                            type="password"
                        />
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
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
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "ViewUsers" ? (
                    <div className="min-w-[min(34rem,88vw)]">
                        <div className={dlgHeading}>View Users</div>
                        <DataTable
                            columns={[
                                "Username / Email",
                                "Role",
                                "Locked",
                                "API",
                            ]}
                            rows={props.users.map((u) => [
                                u.email,
                                u.role,
                                u.locked ? "Yes" : "No",
                                u.api_access ? "Yes" : "No",
                            ])}
                        />
                        <button
                            className={dlgClose}
                            onClick={props.closeDialog}
                        >
                            Close
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "AddUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add User</div>
                        <div className={dlgLabel}>Email</div>
                        <input id="txtName" className={dlgInput} type="text" />
                        <div className={dlgLabel}>Role</div>
                        <select id="ddRole" className={dlgSelect}>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
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
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "DeleteUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Delete User</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>

                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgDanger}
                            onClick={() =>
                                props.confirmDeleteUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Delete User
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

                {props.currentForm === "ConfirmDeleteUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Are you sure you want to delete{" "}
                            {props.userToDelete.email}?
                        </div>
                        <button
                            className={dlgDanger}
                            onClick={props.deleteSelectedUser}
                        >
                            Delete User
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

                {props.currentForm === "LockUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Lock User</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.lockUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Lock User
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

                {props.currentForm === "UnlockUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Unlock User</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.unlockUser(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Unlock User
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
                {props.currentForm === "UserRole" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Change Role</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        <div className={dlgLabel}>Select role</div>
                        <select id="ddRole" className={dlgSelect}>
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                        <button
                            className={dlgPrimary}
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
                            className={dlgCancel}
                            onClick={props.closeDialog}
                        >
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "ResetUser" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Reset User Password</div>
                        <div className={dlgLabel}>User</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.resetUserPassword(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Reset Password
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

                {props.currentForm === "ServerLogs" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Download Server Logs</div>
                        <div className={dlgLabel}>Select service</div>
                        <select id="ddService" className={dlgSelect}>
                            <option value="dcs">
                                Session Capture Server
                            </option>
                            <option value="aps">
                                Audio Processing Service
                            </option>
                        </select>
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.downloadServerLogs(
                                    document.getElementById("ddService").value,
                                )
                            }
                        >
                            Download logs
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

                {props.currentForm === "DeviceLogs" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Download Device Logs</div>
                        <div className={dlgLabel}>Select device</div>
                        <select id="ddDevice" className={dlgSelect}>
                            {props.devices.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.name}
                                </option>
                            ))}
                        </select>
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.downloadDeviceLogs(
                                    document.getElementById("ddDevice").value,
                                )
                            }
                        >
                            Download logs
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

                {props.currentForm === "DeleteServerLogs" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Clear Server Logs</div>
                        <div className={dlgLabel}>Select service</div>
                        <select id="ddService" className={dlgSelect}>
                            <option value="dcs">
                                Session Capture Server
                            </option>
                            <option value="aps">
                                Audio Processing Service
                            </option>
                        </select>
                        <button
                            className={dlgDanger}
                            onClick={() =>
                                props.deleteServerLogs(
                                    document.getElementById("ddService").value,
                                )
                            }
                        >
                            Clear logs
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

                {props.currentForm === "DeleteDeviceLogs" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Clear Device Logs</div>
                        <div className={dlgLabel}>Select device</div>
                        <select id="ddDevice" className={dlgSelect}>
                            {props.devices.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.name}
                                </option>
                            ))}
                        </select>
                        <button
                            className={dlgDanger}
                            onClick={() =>
                                props.deleteDeviceLogs(
                                    document.getElementById("ddDevice").value,
                                )
                            }
                        >
                            Clear logs
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

                {props.currentForm === "AllowAPI" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Allow API Access</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                props.allowAPIAccess(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Allow
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

                {props.currentForm === "RevokeAPI" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Revoke API Access</div>
                        <div className={dlgLabel}>Select user</div>
                        <select id="ddUser" className={dlgSelect}>
                            {props.users.map((u, index) => (
                                <option key={index} value={u.id}>
                                    {u.email}
                                </option>
                            ))}
                        </select>
                        {props.status ? (
                            <div className={dlgError}>{props.status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgDanger}
                            onClick={() =>
                                props.revokeAPIAccess(
                                    document.getElementById("ddUser").value,
                                )
                            }
                        >
                            Revoke
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
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Loading...please wait...
                        </div>
                    </div>
                ) : (
                    <></>
                )}

                {props.currentForm === "Status" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>{props.statusTitle}</div>
                        <div>{props.status}</div>
                        <button
                            className={dlgCancel}
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
