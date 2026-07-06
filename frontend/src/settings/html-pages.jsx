import { Appheader } from "../header/header-component"
import { dlgHeading, dlgBody, dlgLabel, dlgInput, dlgSelect, dlgPrimary, dlgCancel, dlgError, dlgDanger } from "../components/dialog-styles"
import { GenericDialogBox } from "../dialog/dialog-component"

const SECTIONS = [
    {
        title: "Account",
        show: () => true,
        items: [
            { label: "Change Password", dialog: ["ChangePassword"] },
            { label: "Change Email", dialog: ["ChangeEmail"] },
            { label: "Sign Out", signOut: true, danger: true },
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
            <div role="main" className="main-container">
                <Appheader
                    title={"Settings"}
                    leftText={false}
                    rightText={""}
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
                                                    item.signOut
                                                        ? props.signOut()
                                                        : props.openDialog(
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

            <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
                {props.currentForm === "ChangePassword" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Change Password</div>
                        <label htmlFor="txtCurrent" className={dlgLabel}>Current password</label>
                        <input
                            id="txtCurrent"
                            className={dlgInput}
                            type="password"
                        />
                        <label htmlFor="txtNew" className={dlgLabel}>New password</label>
                        <input
                            id="txtNew"
                            className={dlgInput}
                            type="password"
                        />
                        <label htmlFor="txtConfirm" className={dlgLabel}>Confirm new password</label>
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

                {props.currentForm === "ChangeEmail" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Change Email</div>
                        <label htmlFor="txtNewEmail" className={dlgLabel}>New email</label>
                        <input
                            id="txtNewEmail"
                            className={dlgInput}
                            type="email"
                            autoComplete="email"
                        />
                        <label htmlFor="txtEmailPass" className={dlgLabel}>Current password</label>
                        <input
                            id="txtEmailPass"
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
                                props.changeEmail(
                                    document.getElementById("txtEmailPass").value,
                                    document.getElementById("txtNewEmail").value,
                                )
                            }
                        >
                            Change Email
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
                        <label htmlFor="ddService" className={dlgLabel}>Select service</label>
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
                        <label htmlFor="ddDevice" className={dlgLabel}>Select device</label>
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
                        <label htmlFor="ddService" className={dlgLabel}>Select service</label>
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
                        <label htmlFor="ddDevice" className={dlgLabel}>Select device</label>
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
