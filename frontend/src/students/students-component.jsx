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
import { EmptyState } from "../components/empty-state"
import { AppSpinner } from "../spinner/spinner-component"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { AuthService } from "../services/auth-service"
import { ApiService } from "../services/api-service"
import contextStyle from "../components/context-menu/context-menu.module.css"

// "2026-06-18 14:35:58 UTC" -> Date (or null).
const parseDate = (s) => {
    if (!s) return null
    const d = new Date(s.replace(" UTC", "").replace(" ", "T") + "Z")
    return isNaN(d.getTime()) ? null : d
}

const fmtDate = (s) => {
    const d = parseDate(s)
    if (!d) return "—"
    return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
    })
}

const DAY_MS = 24 * 60 * 60 * 1000

const initials = (s) =>
    `${(s.firstname || "?").slice(0, 1)}${(s.lastname || "?").slice(0, 1)}`.toUpperCase()

function StatCard({ label, value, hint }) {
    return (
        <div className="flex-1 rounded-xl border border-tiilt-line bg-white px-4 py-3">
            <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                {label}
            </div>
            <div className="mt-0.5 text-2xl font-bold text-tiilt-ink">
                {value}
            </div>
            {hint ? (
                <div className="text-xs text-tiilt-muted">{hint}</div>
            ) : null}
        </div>
    )
}

const SORTS = {
    name: (a, b) =>
        `${a.lastname}${a.firstname}`.localeCompare(`${b.lastname}${b.firstname}`),
    sessions: (a, b) => (a.session_count || 0) - (b.session_count || 0),
    // Nulls sort as oldest so "never active" lands at the bottom on desc.
    last_active: (a, b) =>
        (parseDate(a.last_active)?.getTime() || 0) -
        (parseDate(b.last_active)?.getTime() || 0),
    created: (a, b) =>
        (parseDate(a.creation_date)?.getTime() || 0) -
        (parseDate(b.creation_date)?.getTime() || 0),
}

// Student roster with participation stats. Every signed-in user can view it;
// the server scopes regular users to students seen in their own sessions.
// Add / sync / edit / delete are admin-only.
function StudentsComponent(props) {
    const me = props.userdata
    const navigate = useNavigate()
    const canManage = me && (me.isAdmin || me.isSuper)

    const [students, setStudents] = useState(null)
    const [search, setSearch] = useState("")
    const [filter, setFilter] = useState("all") // all | enrolled | not
    const [sort, setSort] = useState({ key: "last_active", dir: "desc" })
    const [currentForm, setCurrentForm] = useState("")
    const [status, setStatus] = useState("")
    const [statusTitle, setStatusTitle] = useState("")
    const [target, setTarget] = useState(null) // student a dialog acts on
    const [activity, setActivity] = useState(null) // drill-down payload
    const [syncEnabled, setSyncEnabled] = useState(false)

    const loadStudents = async () => {
        try {
            const response = await new AuthService().getStudentsOverview()
            setStudents(response.status === 200 ? await response.json() : [])
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

    const stats = useMemo(() => {
        if (!students) return null
        const enrolled = students.filter(
            (s) => s.biometric_captured === "yes",
        ).length
        const cutoff = Date.now() - 30 * DAY_MS
        const active = students.filter((s) => {
            const d = parseDate(s.last_active)
            return d && d.getTime() > cutoff
        }).length
        return { total: students.length, enrolled, active }
    }, [students])

    const visible = useMemo(() => {
        if (students === null) return null
        const q = search.trim().toLowerCase()
        let list = students
        if (filter === "enrolled")
            list = list.filter((s) => s.biometric_captured === "yes")
        if (filter === "not")
            list = list.filter((s) => s.biometric_captured !== "yes")
        if (q)
            list = list.filter((s) =>
                `${s.firstname} ${s.lastname} ${s.username}`
                    .toLowerCase()
                    .includes(q),
            )
        const sorted = [...list].sort(SORTS[sort.key])
        if (sort.dir === "desc") sorted.reverse()
        return sorted
    }, [students, search, filter, sort])

    const toggleSort = (key) =>
        setSort((s) =>
            s.key === key
                ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
                : { key, dir: key === "name" ? "asc" : "desc" },
        )

    const showStatus = (title, message) => {
        setStatusTitle(title)
        setStatus(message)
        setCurrentForm("Status")
    }

    const closeDialog = () => {
        setStatus("")
        setCurrentForm("")
        setTarget(null)
        setActivity(null)
    }

    // Tier C: click a student -> their session history (scoped server-side
    // exactly like the roster).
    const openActivity = async (student) => {
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().getStudentActivity(
                student.id,
            )
            if (response.status === 200) {
                setActivity(await response.json())
                setCurrentForm("Activity")
            } else {
                showStatus(
                    "Couldn't load activity",
                    "The student's session history could not be loaded.",
                )
            }
        } catch {
            showStatus(
                "Couldn't load activity",
                "The server could not be reached.",
            )
        }
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
                showStatus("Student added", username + " has been created.")
            } else {
                let message = "Could not create the student profile."
                try {
                    const err = await response.json()
                    if (err["message"]) message = err["message"]
                } catch {
                    /* non-JSON error body */
                }
                showStatus("Failed to add student", message)
            }
        } catch {
            showStatus(
                "Failed to add student",
                "The server could not be reached.",
            )
        }
    }

    const saveEdit = async (firstname, lastname) => {
        firstname = firstname.trim()
        lastname = lastname.trim()
        if (!firstname || !lastname) {
            setStatus("First and last name are required.")
            return
        }
        setCurrentForm("Loading")
        try {
            const response = await new ApiService().httpRequestCall(
                "api/v1/student/updatestudent",
                "POST",
                {
                    id: target.id,
                    firstname,
                    lastname,
                    biometric_captured: target.biometric_captured,
                },
            )
            if (response.status === 200) {
                await loadStudents()
                showStatus(
                    "Student updated",
                    `${target.username} is now ${firstname} ${lastname}.`,
                )
            } else {
                showStatus(
                    "Failed to update",
                    `${target.username} could not be updated.`,
                )
            }
        } catch {
            showStatus("Failed to update", "The server could not be reached.")
        }
    }

    const deleteStudent = async () => {
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().deleteStudent(target.id)
            if (response.status === 200) {
                await loadStudents()
                showStatus(
                    "Student deleted",
                    target.username + " has been deleted.",
                )
            } else {
                showStatus(
                    "Failed to delete",
                    target.username + " could not be deleted.",
                )
            }
        } catch {
            showStatus("Failed to delete", "The server could not be reached.")
        }
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

    const exportCsv = () => {
        const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`
        const lines = [
            "First name,Last name,Username,Enrolled,Sessions,Last active,Created",
            ...(visible || []).map((s) =>
                [
                    esc(s.firstname),
                    esc(s.lastname),
                    esc(s.username),
                    s.biometric_captured === "yes" ? "yes" : "no",
                    s.session_count || 0,
                    s.last_active || "",
                    s.creation_date || "",
                ].join(","),
            ),
        ]
        const blob = new Blob([lines.join("\n")], { type: "text/csv" })
        const link = document.createElement("a")
        link.href = URL.createObjectURL(blob)
        link.download = "students.csv"
        link.click()
        URL.revokeObjectURL(link.href)
    }

    const filterChip = (value, label) => (
        <button
            onClick={() => setFilter(value)}
            aria-pressed={filter === value}
            className={
                "cursor-pointer rounded-full px-3 py-1 text-xs font-semibold transition " +
                (filter === value
                    ? "bg-tiilt text-white"
                    : "bg-tiilt-line/40 text-tiilt-muted hover:bg-tiilt-soft hover:text-tiilt")
            }
        >
            {label}
        </button>
    )

    const sortHeader = (key, label, alignRight = false) => (
        <th
            aria-sort={
                sort.key === key
                    ? sort.dir === "asc"
                        ? "ascending"
                        : "descending"
                    : undefined
            }
            className={
                "sticky top-0 bg-tiilt-ground px-4 py-2.5 whitespace-nowrap " +
                (alignRight ? "text-right" : "text-left")
            }
        >
            <button
                onClick={() => toggleSort(key)}
                className="cursor-pointer font-semibold text-tiilt-ink transition hover:text-tiilt"
            >
                {label}
                <span
                    aria-hidden="true"
                    className={
                        "ml-1 inline-block text-[10px] " +
                        (sort.key === key
                            ? "text-tiilt"
                            : "text-tiilt-line")
                    }
                >
                    {sort.key === key && sort.dir === "asc" ? "▲" : "▼"}
                </span>
            </button>
        </th>
    )

    return (
        <>
            <div role="main" className="main-container">
                <Appheader
                    title={"Students"}
                    leftText={false}
                    rightText={""}
                    nav={() => navigate("/home")}
                />
                <div className="relative min-h-0 w-full grow overflow-y-auto bg-tiilt-ground/60">
                    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-8">
                        {!canManage ? (
                            <div className="rounded-lg bg-tiilt-soft/60 px-4 py-3 text-sm text-tiilt-muted">
                                Showing students who have participated in your
                                sessions. Session counts and activity reflect
                                your sessions only.
                            </div>
                        ) : null}

                        {stats ? (
                            <div className="flex flex-col gap-3 sm:flex-row">
                                <StatCard label="Students" value={stats.total} />
                                <StatCard
                                    label="Enrolled"
                                    value={stats.enrolled}
                                    hint={
                                        stats.total
                                            ? `${Math.round((stats.enrolled / stats.total) * 100)}% of roster`
                                            : undefined
                                    }
                                />
                                <StatCard
                                    label="Active last 30 days"
                                    value={stats.active}
                                />
                            </div>
                        ) : null}

                        <div className="flex flex-wrap items-center gap-3">
                            <input
                                type="search"
                                value={search}
                                onInput={(e) => setSearch(e.target.value)}
                                placeholder="Search students…"
                                aria-label="Search students"
                                className="h-10 w-full max-w-60 rounded-lg border border-tiilt-line bg-white px-3 text-sm text-tiilt-ink transition outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30"
                            />
                            <div className="flex items-center gap-1.5">
                                {filterChip("all", "All")}
                                {filterChip("enrolled", "Enrolled")}
                                {filterChip("not", "Not enrolled")}
                            </div>
                            <div className="ml-auto flex gap-2">
                                <button
                                    className={btnSecondary}
                                    onClick={exportCsv}
                                    title="Download the current view as CSV"
                                >
                                    Export CSV
                                </button>
                                {canManage && syncEnabled ? (
                                    <button
                                        className={btnSecondary}
                                        onClick={syncStudents}
                                        title="Push this instance's student roster to the configured peer deployment"
                                    >
                                        Sync
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

                        {students === null ? (
                            <div className="flex justify-center py-10">
                                <AppSpinner />
                            </div>
                        ) : visible.length === 0 ? (
                            <div className="rounded-xl border border-tiilt-line bg-white">
                                <EmptyState
                                    title="No students match"
                                    subtitle={
                                        students.length === 0
                                            ? "Students appear here after they enroll a fingerprint in a session."
                                            : "Try a different search or filter."
                                    }
                                />
                            </div>
                        ) : (
                            <div className="overflow-x-auto rounded-xl border border-tiilt-line bg-white">
                                <table className="w-full border-collapse text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-tiilt-line">
                                            {sortHeader("name", "Student")}
                                            <th className="sticky top-0 bg-tiilt-ground px-4 py-2.5 text-left font-semibold whitespace-nowrap text-tiilt-ink">
                                                Enrolled
                                            </th>
                                            {sortHeader(
                                                "sessions",
                                                "Sessions",
                                                true,
                                            )}
                                            {sortHeader(
                                                "last_active",
                                                "Last active",
                                            )}
                                            {sortHeader("created", "Created")}
                                            <th className="sticky top-0 bg-tiilt-ground px-4 py-2.5">
                                                <span className="sr-only">
                                                    Actions
                                                </span>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {visible.map((s) => (
                                            <tr
                                                key={s.id}
                                                onClick={() => openActivity(s)}
                                                title={`View ${s.firstname}'s session history`}
                                                className="cursor-pointer border-t border-tiilt-line bg-white transition first:border-t-0 hover:bg-tiilt-soft/50"
                                            >
                                                <td className="px-4 py-2.5">
                                                    <div className="flex items-center gap-3">
                                                        <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-tiilt-soft text-xs font-bold text-tiilt">
                                                            {initials(s)}
                                                        </span>
                                                        <span className="min-w-0">
                                                            <span className="block truncate font-semibold text-tiilt-ink">
                                                                {s.firstname}{" "}
                                                                {s.lastname}
                                                            </span>
                                                            <span className="block truncate font-ahamono text-xs text-tiilt-muted">
                                                                {s.username}
                                                            </span>
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-2.5">
                                                    {s.biometric_captured ===
                                                    "yes" ? (
                                                        <StatusPill
                                                            tone="teal"
                                                            dot
                                                        >
                                                            Enrolled
                                                        </StatusPill>
                                                    ) : (
                                                        <StatusPill
                                                            tone="orange"
                                                            dot
                                                        >
                                                            Not enrolled
                                                        </StatusPill>
                                                    )}
                                                </td>
                                                <td className="px-4 py-2.5 text-right font-ahamono tabular-nums text-tiilt-ink">
                                                    {s.session_count > 0 ? (
                                                        s.session_count
                                                    ) : (
                                                        <span className="text-tiilt-muted">
                                                            0
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-4 py-2.5 whitespace-nowrap text-tiilt-ink">
                                                    {fmtDate(s.last_active)}
                                                </td>
                                                <td className="px-4 py-2.5 whitespace-nowrap text-tiilt-muted">
                                                    {fmtDate(s.creation_date)}
                                                </td>
                                                <td
                                                    className="px-2 py-2.5 text-right"
                                                    onClick={(e) =>
                                                        e.stopPropagation()
                                                    }
                                                >
                                                    <AppContextMenu
                                                        label={`Actions for ${s.username}`}
                                                    >
                                                        <button
                                                            role="menuitem"
                                                            className={
                                                                contextStyle[
                                                                    "menu-item"
                                                                ]
                                                            }
                                                            onClick={() =>
                                                                openActivity(s)
                                                            }
                                                        >
                                                            View activity
                                                        </button>
                                                        {canManage ? (
                                                            <button
                                                                role="menuitem"
                                                                className={
                                                                    contextStyle[
                                                                        "menu-item"
                                                                    ]
                                                                }
                                                                onClick={() => {
                                                                    setTarget(s)
                                                                    setCurrentForm(
                                                                        "EditStudent",
                                                                    )
                                                                }}
                                                            >
                                                                Edit name
                                                            </button>
                                                        ) : null}
                                                        {canManage ? (
                                                            <button
                                                                role="menuitem"
                                                                className={`${contextStyle["menu-item"]} ${contextStyle["red"]}`}
                                                                onClick={() => {
                                                                    setTarget(s)
                                                                    setCurrentForm(
                                                                        "ConfirmDeleteStudent",
                                                                    )
                                                                }}
                                                            >
                                                                Delete
                                                            </button>
                                                        ) : null}
                                                    </AppContextMenu>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <GenericDialogBox onClose={closeDialog} show={currentForm !== ""}>
                {currentForm === "AddStudent" ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>Add student</div>
                        <label htmlFor="stuFirstname" className={dlgLabel}>
                            First name
                        </label>
                        <input
                            id="stuFirstname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                        />
                        <label htmlFor="stuLastname" className={dlgLabel}>
                            Last name
                        </label>
                        <input
                            id="stuLastname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                        />
                        <label htmlFor="stuUsername" className={dlgLabel}>
                            Username (5-10 characters)
                        </label>
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
                            Create student
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "EditStudent" && target ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Edit {target.username}
                        </div>
                        <label htmlFor="editFirstname" className={dlgLabel}>
                            First name
                        </label>
                        <input
                            id="editFirstname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                            defaultValue={target.firstname}
                        />
                        <label htmlFor="editLastname" className={dlgLabel}>
                            Last name
                        </label>
                        <input
                            id="editLastname"
                            className={dlgInput}
                            type="text"
                            maxLength={50}
                            defaultValue={target.lastname}
                        />
                        {status ? (
                            <div className={dlgError}>{status}</div>
                        ) : null}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                saveEdit(
                                    document.getElementById("editFirstname")
                                        .value,
                                    document.getElementById("editLastname")
                                        .value,
                                )
                            }
                        >
                            Save changes
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "Activity" && activity ? (
                    <div className="flex min-w-[min(33rem,86vw)] flex-col gap-3">
                        <div className={dlgHeading}>
                            {activity.student.firstname}{" "}
                            {activity.student.lastname}
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-tiilt-muted">
                            <span className="font-ahamono">
                                {activity.student.username}
                            </span>
                            <span>
                                {activity.sessions.length}{" "}
                                {activity.sessions.length === 1
                                    ? "session"
                                    : "sessions"}
                            </span>
                            {activity.llm_reports > 0 ? (
                                <span>
                                    {activity.llm_reports} LLM feedback{" "}
                                    {activity.llm_reports === 1
                                        ? "report"
                                        : "reports"}
                                </span>
                            ) : null}
                        </div>
                        {activity.sessions.length === 0 ? (
                            <div className="rounded-lg bg-tiilt-soft/60 px-4 py-6 text-center text-sm text-tiilt-muted">
                                No session participation yet — they'll appear
                                here once they enroll a fingerprint in a
                                session.
                            </div>
                        ) : (
                            <DataTable
                                columns={["Session", "Date", "Group", ""]}
                                rows={activity.sessions.map((s) => [
                                    s.session_name,
                                    fmtDate(s.creation_date),
                                    s.group_name,
                                    s.owned ? (
                                        <button
                                            key="open"
                                            className="rounded-md px-2 py-1 text-xs font-semibold text-tiilt transition hover:bg-tiilt-soft"
                                            onClick={() =>
                                                navigate(
                                                    `/sessions/${s.session_id}/pods/${s.session_device_id}`,
                                                )
                                            }
                                        >
                                            Open ›
                                        </button>
                                    ) : (
                                        <span
                                            key="open"
                                            className="text-xs text-tiilt-muted"
                                            title="Owned by another user"
                                        >
                                            —
                                        </span>
                                    ),
                                ])}
                            />
                        )}
                        <button className={dlgCancel} onClick={closeDialog}>
                            Close
                        </button>
                    </div>
                ) : null}

                {currentForm === "ConfirmDeleteStudent" && target ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Delete {target.username}?
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            This removes the student profile and its enrolled
                            biometrics.
                        </div>
                        <button className={dlgDanger} onClick={deleteStudent}>
                            Delete student
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
