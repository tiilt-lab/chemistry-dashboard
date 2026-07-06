import { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import {
    dlgHeading,
    dlgBody,
    dlgLabel,
    dlgInput,
    dlgPrimary,
    dlgDanger,
    dlgCancel,
    dlgError,
    btnPrimary,
    btnSecondary,
} from "../components/dialog-styles"
import { Appheader } from "../header/header-component"
import { GenericDialogBox } from "../dialog/dialog-component"
import { DataTable } from "../components/data-table"
import { StatusPill } from "../components/status-pill"
import { AppSpinner } from "../spinner/spinner-component"
import { AuthService } from "../services/auth-service"
import { ApiService } from "../services/api-service"

const rowDeleteClass =
    "rounded-md px-2 py-1 text-xs font-semibold text-tiilt-danger transition hover:bg-tiilt-danger-soft"

// "2026-06-18 14:35:58 UTC" -> short local date, or em dash.
const fmtDate = (s) => {
    if (!s) return "—"
    const d = new Date(s.replace(" UTC", "").replace(" ", "T") + "Z")
    if (isNaN(d.getTime())) return "—"
    return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
    })
}

// Student roster with participation stats. Every signed-in user can view it;
// the server scopes regular users to students seen in their own sessions.
// Add / sync / delete are admin-only.
function StudentsComponent(props) {
    const me = props.userdata
    const navigate = useNavigate()
    const canManage = me && (me.isAdmin || me.isSuper)

    const [students, setStudents] = useState(null)
    const [search, setSearch] = useState("")
    const [currentForm, setCurrentForm] = useState("")
    const [status, setStatus] = useState("")
    const [statusTitle, setStatusTitle] = useState("")
    const [toDelete, setToDelete] = useState(null)
    const [syncEnabled, setSyncEnabled] = useState(false)

    const loadStudents = async () => {
        try {
            const response = await new AuthService().getStudentsOverview()
            if (response.status === 200) {
                setStudents(await response.json())
            } else {
                setStudents([])
            }
        } catch {
            setStudents([])
        }
    }

    useEffect(() => {
        loadStudents()
        if (canManage) {
            new AuthService()
                .syncEnabled()
                .then((r) => (r.status === 200 ? r.json() : { enabled: false }))
                .then((d) => setSyncEnabled(!!d.enabled))
                .catch(() => setSyncEnabled(false))
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const visible = useMemo(() => {
        if (students === null) return null
        const q = search.trim().toLowerCase()
        const filtered = q
            ? students.filter((s) =>
                  `${s.firstname} ${s.lastname} ${s.username}`
                      .toLowerCase()
                      .includes(q),
              )
            : students
        // Most recently active first; never-active students sink to the end
        // (sorted by name) so newcomers who still need enrolling stand out.
        return [...filtered].sort((a, b) => {
            if (a.last_active && b.last_active)
                return a.last_active < b.last_active ? 1 : -1
            if (a.last_active) return -1
            if (b.last_active) return 1
            return `${a.lastname}${a.firstname}`.localeCompare(
                `${b.lastname}${b.firstname}`,
            )
        })
    }, [students, search])

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
                { firstname, lastname, username },
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

    const columns = [
        "Name",
        "Username",
        "Enrolled",
        "Sessions",
        "Last active",
        "Created",
    ]
    if (canManage) columns.push("")

    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Students"}
                    leftText={false}
                    rightText={""}
                    nav={() => navigate("/home")}
                />
                <div className="relative min-h-0 w-full grow overflow-y-auto">
                    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-8">
                        {!canManage ? (
                            <div className="rounded-lg bg-tiilt-soft/60 px-4 py-3 text-sm text-tiilt-muted">
                                Showing students who have participated in your
                                sessions. Session counts and activity reflect
                                your sessions only.
                            </div>
                        ) : null}
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <span className="text-sm text-tiilt-muted">
                                {students === null
                                    ? "Loading…"
                                    : `${visible.length} of ${students.length} ${students.length === 1 ? "student" : "students"}`}
                            </span>
                            <div className="flex gap-2">
                                {canManage && syncEnabled ? (
                                    <button
                                        className={btnSecondary}
                                        onClick={syncStudents}
                                        title="Push this instance's student roster to the configured peer deployment"
                                    >
                                        Sync profiles
                                    </button>
                                ) : null}
                                {canManage ? (
                                    <button
                                        className={btnPrimary}
                                        onClick={() =>
                                            setCurrentForm("AddStudent")
                                        }
                                    >
                                        Add student
                                    </button>
                                ) : null}
                            </div>
                        </div>
                        <input
                            type="search"
                            value={search}
                            onInput={(e) => setSearch(e.target.value)}
                            placeholder="Search students…"
                            aria-label="Search students"
                            className="h-10 w-full max-w-xs rounded-lg border border-tiilt-line bg-white px-3 text-sm text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                        />

                        {students === null ? (
                            <div className="flex justify-center py-10">
                                <AppSpinner />
                            </div>
                        ) : (
                            <DataTable
                                columns={columns}
                                rows={visible.map((s) => {
                                    const row = [
                                        `${s.firstname} ${s.lastname}`,
                                        s.username,
                                        s.biometric_captured === "yes" ? (
                                            <StatusPill
                                                key="en"
                                                tone="teal"
                                                dot
                                            >
                                                Enrolled
                                            </StatusPill>
                                        ) : (
                                            <StatusPill
                                                key="en"
                                                tone="orange"
                                                dot
                                            >
                                                Not enrolled
                                            </StatusPill>
                                        ),
                                        s.session_count > 0 ? (
                                            s.session_count
                                        ) : (
                                            <span
                                                key="sc"
                                                className="text-tiilt-muted"
                                            >
                                                0
                                            </span>
                                        ),
                                        fmtDate(s.last_active),
                                        fmtDate(s.creation_date),
                                    ]
                                    if (canManage) {
                                        row.push(
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
                                        )
                                    }
                                    return row
                                })}
                            />
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
                        ) : null}
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
                ) : null}

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

export { StudentsComponent }
