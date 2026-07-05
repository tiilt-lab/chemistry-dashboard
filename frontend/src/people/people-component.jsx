import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { DataTable } from "../components/data-table"
import { AppSpinner } from "../spinner/spinner-component"
import { AuthService } from "../services/auth-service"
import { ApiService } from "../services/api-service"
import { StudentModel } from "../models/student"
import { RaterModel } from "../models/rater"

const dlgHeading = "mb-3 text-lg font-semibold text-tiilt-ink"
const dlgBody = "flex min-w-[min(22rem,86vw)] flex-col gap-3"
const dlgLabel = "text-sm font-semibold text-tiilt-ink"
const dlgInput =
    "h-11 w-full rounded-lg border border-tiilt-line bg-white px-3 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
const dlgSelect =
    "h-11 w-full cursor-pointer rounded-lg border border-tiilt-line bg-white px-3 pr-8 text-base text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
const dlgPrimary =
    "mt-2 h-11 rounded-lg bg-tiilt font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
const dlgDanger =
    "mt-2 h-11 rounded-lg bg-tiilt-danger font-semibold text-white transition hover:brightness-90 active:translate-y-px"
const dlgCancel =
    "h-11 rounded-lg border border-tiilt-line bg-white font-semibold text-tiilt-ink transition hover:bg-tiilt-soft active:translate-y-px"
const dlgError =
    "rounded-md bg-tiilt-danger-soft px-3 py-2 text-sm text-tiilt-danger"

const rowDeleteClass =
    "rounded-md px-2 py-1 text-xs font-semibold text-tiilt-danger transition hover:bg-tiilt-danger-soft"
const primaryBtn =
    "rounded-lg bg-tiilt px-4 py-2 text-sm font-semibold text-white transition hover:bg-tiilt-deep active:translate-y-px"
const secondaryBtn =
    "rounded-lg border border-tiilt-line bg-white px-4 py-2 text-sm font-semibold text-tiilt-ink transition hover:border-tiilt hover:bg-tiilt-soft active:translate-y-px"

function PeopleComponent() {
    const navigate = useNavigate()
    const [tab, setTab] = useState("students")
    const [students, setStudents] = useState(null)
    const [raters, setRaters] = useState(null)
    const [currentForm, setCurrentForm] = useState("")
    const [status, setStatus] = useState("")
    const [statusTitle, setStatusTitle] = useState("")
    const [toDelete, setToDelete] = useState(null)
    const [syncEnabled, setSyncEnabled] = useState(false)

    const loadStudents = async () => {
        try {
            const response = await new AuthService().getStudentProfiles()
            if (response.status === 200) {
                setStudents(StudentModel.fromJsonList(await response.json()))
            }
        } catch {
            setStudents([])
        }
    }

    const loadRaters = async () => {
        try {
            const response = await new AuthService().getRaters()
            if (response.status === 200) {
                setRaters(RaterModel.fromJsonList(await response.json()))
            }
        } catch {
            setRaters([])
        }
    }

    useEffect(() => {
        loadStudents()
        loadRaters()
        new AuthService()
            .syncEnabled()
            .then((r) => (r.status === 200 ? r.json() : { enabled: false }))
            .then((d) => setSyncEnabled(!!d.enabled))
            .catch(() => setSyncEnabled(false))
    }, [])

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

    const addStudent = async (firstname, lastname, username) => {
        firstname = firstname.trim()
        lastname = lastname.trim()
        username = username.trim()
        if (!firstname || !lastname || !username) {
            setStatus("Please fill in first name, last name, and username.")
            return
        }
        if (username.length < 5 || username.length > 10) {
            setStatus("Username must be 5-10 characters.")
            return
        }
        setCurrentForm("Loading")
        try {
            const response = await new ApiService().httpRequestCall(
                "api/v1/student/addstudent",
                "POST",
                {
                    firstname: firstname,
                    lastname: lastname,
                    username: username,
                },
            )
            if (response.status === 200) {
                await loadStudents()
                showStatus("Student Added", username + " has been created.")
            } else {
                let message = "Could not create the student profile."
                try {
                    const err = await response.json()
                    if (err["message"]) message = err["message"]
                } catch {
                    /* non-JSON error body */
                }
                showStatus("Failed to Add Student", message)
            }
        } catch {
            showStatus(
                "Failed to Add Student",
                "The server could not be reached.",
            )
        }
    }

    const deleteStudent = async () => {
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().deleteStudent(toDelete.id)
            if (response.status === 200) {
                await loadStudents()
                showStatus(
                    "Student Deleted",
                    toDelete.username + " has been deleted.",
                )
            } else {
                showStatus(
                    "Failed to Delete",
                    toDelete.username + " could not be deleted.",
                )
            }
        } catch {
            showStatus("Failed to Delete", "The server could not be reached.")
        }
        setToDelete(null)
    }

    const syncStudents = async () => {
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().syncStudentProfile()
            if (response.status === 200) {
                await loadStudents()
                showStatus("Success", "Student profile syncing completed.")
            } else {
                showStatus("Error", "Student profile syncing failed.")
            }
        } catch {
            showStatus("Error", "The server could not be reached.")
        }
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

    const tabClass = (active) =>
        "rounded-lg px-4 py-2 text-sm font-semibold transition " +
        (active
            ? "bg-tiilt text-white"
            : "text-tiilt-muted hover:bg-tiilt-soft hover:text-tiilt")

    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Students & Raters"}
                    leftText={false}
                    rightText={""}
                    rightEnabled={false}
                    nav={() => navigate("/home")}
                />
                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-8">
                        <div className="flex items-center gap-2">
                            <button
                                className={tabClass(tab === "students")}
                                onClick={() => setTab("students")}
                            >
                                Students
                            </button>
                            <button
                                className={tabClass(tab === "raters")}
                                onClick={() => setTab("raters")}
                            >
                                Raters
                            </button>
                        </div>

                        {tab === "students" ? (
                            <section className="flex flex-col gap-3">
                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-sm text-tiilt-muted">
                                        {students === null
                                            ? "Loading…"
                                            : `${students.length} ${students.length === 1 ? "student" : "students"}`}
                                    </span>
                                    <div className="flex gap-2">
                                        {syncEnabled ? (
                                            <button
                                                className={secondaryBtn}
                                                onClick={syncStudents}
                                                title="Push this instance's student roster to the configured peer deployment"
                                            >
                                                Sync profiles
                                            </button>
                                        ) : (
                                            <></>
                                        )}
                                        <button
                                            className={primaryBtn}
                                            onClick={() =>
                                                setCurrentForm("AddStudent")
                                            }
                                        >
                                            Add student
                                        </button>
                                    </div>
                                </div>
                                {students === null ? (
                                    <div className="flex justify-center py-10">
                                        <AppSpinner />
                                    </div>
                                ) : (
                                    <DataTable
                                        columns={[
                                            "Username",
                                            "First Name",
                                            "Last Name",
                                            "",
                                        ]}
                                        rows={students.map((s) => [
                                            s.username,
                                            s.firstname,
                                            s.lastname,
                                            <button
                                                key="del"
                                                className={rowDeleteClass}
                                                onClick={() => {
                                                    setToDelete(s)
                                                    setCurrentForm(
                                                        "ConfirmDeleteStudent",
                                                    )
                                                }}
                                            >
                                                Delete
                                            </button>,
                                        ])}
                                    />
                                )}
                            </section>
                        ) : (
                            <section className="flex flex-col gap-3">
                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-sm text-tiilt-muted">
                                        {raters === null
                                            ? "Loading…"
                                            : `${raters.length} ${raters.length === 1 ? "rater" : "raters"}`}
                                    </span>
                                    <button
                                        className={primaryBtn}
                                        onClick={() =>
                                            setCurrentForm("AddRater")
                                        }
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
                            </section>
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={closeDialog} show={currentForm !== ""}>
                {currentForm === "AddStudent" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add Student Profile</div>
                        <div className={dlgLabel}>First name</div>
                        <input
                            id="stuFirstname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                        />
                        <div className={dlgLabel}>Last name</div>
                        <input
                            id="stuLastname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                        />
                        <div className={dlgLabel}>
                            Username (5-10 characters)
                        </div>
                        <input
                            id="stuUsername"
                            className={dlgInput}
                            type="text"
                            minLength={5}
                            maxLength={10}
                        />
                        {status ? (
                            <div className={dlgError}>{status}</div>
                        ) : (
                            <></>
                        )}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                addStudent(
                                    document.getElementById("stuFirstname")
                                        .value,
                                    document.getElementById("stuLastname")
                                        .value,
                                    document.getElementById("stuUsername")
                                        .value,
                                )
                            }
                        >
                            Create Student
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

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
                        ) : (
                            <></>
                        )}
                        <button className={dlgPrimary} onClick={addRater}>
                            Create Rater
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

                {currentForm === "ConfirmDeleteStudent" && toDelete ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Delete {toDelete.username}?
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            This removes the student profile and its enrolled
                            biometrics.
                        </div>
                        <button className={dlgDanger} onClick={deleteStudent}>
                            Delete Student
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : (
                    <></>
                )}

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
                ) : (
                    <></>
                )}

                {currentForm === "Loading" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Working…</div>
                        <div className="flex justify-center py-4">
                            <AppSpinner />
                        </div>
                    </div>
                ) : (
                    <></>
                )}

                {currentForm === "Status" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>{statusTitle}</div>
                        <div className="text-sm text-tiilt-ink">{status}</div>
                        <button className={dlgCancel} onClick={closeDialog}>
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

export { PeopleComponent }
