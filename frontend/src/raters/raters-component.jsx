import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import {
    dlgHeading,
    dlgBody,
    dlgLabel,
    dlgInput,
    dlgSelect,
    dlgPrimary,
    dlgDanger,
    dlgCancel,
    dlgError,
    btnPrimary,
} from "../components/dialog-styles"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { DataTable } from "../components/data-table"
import { AppSpinner } from "../spinner/spinner-component"
import { AuthService } from "../services/auth-service"
import { RaterModel } from "../models/rater"
import { useRequireManager } from "../routes/roles"
import { AdminTabs } from "../components/admin-tabs"

const rowDeleteClass =
    "rounded-md px-2 py-1 text-xs font-semibold text-tiilt-danger transition hover:bg-tiilt-danger-soft"

// Expert raters assigned to score session dashboards. Admin-only.
function RatersComponent(props) {
    const me = props.userdata
    const navigate = useNavigate()
    const canManage = useRequireManager(me)

    const [raters, setRaters] = useState(null)
    const [currentForm, setCurrentForm] = useState("")
    const [status, setStatus] = useState("")
    const [statusTitle, setStatusTitle] = useState("")
    const [toDelete, setToDelete] = useState(null)

    useEffect(() => {
        if (!canManage) return
        loadRaters()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const loadRaters = async () => {
        try {
            const response = await new AuthService().getRaters()
            if (response.status === 200) {
                setRaters(RaterModel.fromJsonList(await response.json()))
            } else {
                setRaters([])
            }
        } catch {
            setRaters([])
        }
    }

    const showStatus = (title, message) => {
        setStatusTitle(title)
        setStatus(message)
        setCurrentForm("Status")
    }

    const closeDialog = () => {
        setStatus("")
        setCurrentForm("")
        setToDelete(null)
    }

    const addRater = async () => {
        const val = (id) => document.getElementById(id).value.trim()
        if (!val("sessionId") || !val("raterId")) {
            setStatus("Session ID and Rater ID are required.")
            return
        }
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().createRater(
                val("sessionId"),
                val("sessionDeviceId"),
                val("speakerId"),
                val("speakertag"),
                val("raterId"),
                document.getElementById("type").value,
                document.getElementById("evaluationcategory").value,
            )
            if (response.status === 200) {
                await loadRaters()
                showStatus(
                    "Rater Created",
                    "The rater was created successfully.",
                )
            } else {
                let message = "Could not create the rater."
                try {
                    const err = await response.json()
                    if (err["message"]) message = err["message"]
                } catch {
                    /* non-JSON error body */
                }
                showStatus("Failed to Create Rater", message)
            }
        } catch {
            showStatus(
                "Failed to Create Rater",
                "The server could not be reached.",
            )
        }
    }

    const deleteRater = async () => {
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().deleteRater(toDelete.id)
            if (response.status === 200) {
                await loadRaters()
                showStatus("Rater Deleted", "The rater has been deleted.")
            } else {
                showStatus(
                    "Failed to Delete",
                    "The rater could not be deleted.",
                )
            }
        } catch {
            showStatus("Failed to Delete", "The server could not be reached.")
        }
        setToDelete(null)
    }

    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Admin"}
                    leftText={false}
                    rightText={""}
                    nav={() => navigate("/home")}
                />
                <AdminTabs />
                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-8">
                        <div className="flex items-center justify-between gap-3">
                            <span className="text-sm text-tiilt-muted">
                                {raters === null
                                    ? "Loading…"
                                    : `${raters.length} ${raters.length === 1 ? "rater" : "raters"}`}
                            </span>
                            <button
                                className={btnPrimary}
                                onClick={() => setCurrentForm("AddRater")}
                            >
                                Add rater
                            </button>
                        </div>
                        {raters === null ? (
                            <div className="flex justify-center py-10">
                                <AppSpinner />
                            </div>
                        ) : (
                            <DataTable
                                columns={[
                                    "Rater",
                                    "Session",
                                    "Device",
                                    "Speaker",
                                    "Tag",
                                    "Type",
                                    "",
                                ]}
                                rows={raters.map((r) => [
                                    r.raterid,
                                    r.sessionid,
                                    r.sessiondeviceid,
                                    r.speakerid,
                                    r.speakertag,
                                    r.dashboardtype,
                                    <button
                                        key="del"
                                        className={rowDeleteClass}
                                        onClick={() => {
                                            setToDelete(r)
                                            setCurrentForm(
                                                "ConfirmDeleteRater",
                                            )
                                        }}
                                    >
                                        Delete
                                    </button>,
                                ])}
                            />
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={closeDialog} show={currentForm !== ""}>
                {currentForm === "AddRater" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add Rater</div>
                        <div className={dlgLabel}>Session ID</div>
                        <input
                            id="sessionId"
                            className={dlgInput}
                            type="text"
                        />
                        <div className={dlgLabel}>Session Device ID</div>
                        <input
                            id="sessionDeviceId"
                            className={dlgInput}
                            type="text"
                        />
                        <div className={dlgLabel}>Speaker ID</div>
                        <input
                            id="speakerId"
                            className={dlgInput}
                            type="text"
                        />
                        <div className={dlgLabel}>Speaker Tag</div>
                        <input
                            id="speakertag"
                            className={dlgInput}
                            type="text"
                        />
                        <div className={dlgLabel}>Rater ID</div>
                        <input id="raterId" className={dlgInput} type="text" />
                        <div className={dlgLabel}>Dashboard Type</div>
                        <select id="type" className={dlgSelect}>
                            <option value="quantitative">
                                Quantitative Dashboard
                            </option>
                            <option value="reflection">
                                Reflection Dashboard
                            </option>
                        </select>
                        <div className={dlgLabel}>Evaluation Category</div>
                        <select id="evaluationcategory" className={dlgSelect}>
                            <option value="visualization">Visualization</option>
                            <option value="reflection">Reflection</option>
                            <option value="multimodal">Multimodal</option>
                            <option value="unimodal">Unimodal</option>
                            <option value="structured">Structured</option>
                            <option value="unstructured">Unstructured</option>
                        </select>
                        {status ? (
                            <div className={dlgError}>{status}</div>
                        ) : null}
                        <button className={dlgPrimary} onClick={addRater}>
                            Create Rater
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "ConfirmDeleteRater" && toDelete ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Delete rater {toDelete.raterid}?
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            Session {toDelete.sessionid} ·{" "}
                            {toDelete.dashboardtype}
                        </div>
                        <button className={dlgDanger} onClick={deleteRater}>
                            Delete Rater
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "Loading" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Working…</div>
                        <div className="flex justify-center py-4">
                            <AppSpinner />
                        </div>
                    </div>
                ) : null}

                {currentForm === "Status" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>{statusTitle}</div>
                        <div className="text-sm text-tiilt-ink">{status}</div>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Close
                        </button>
                    </div>
                ) : null}
            </GenericDialogBox>
        </>
    )
}

export { RatersComponent }
