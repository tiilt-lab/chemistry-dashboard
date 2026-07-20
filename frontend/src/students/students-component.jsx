import { useState, useEffect, useMemo } from "react"
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
import { isManager } from "../routes/roles"
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

// Voice-print state from the overview's enrollment fields (the .check.json
// verdict the audio service writes at capture time / via the survey run).
// Three grades: weak = genuinely broken (near-silent or doesn't match
// itself); short = only fails the net-speech bar (old 10s-cap era — usable,
// but worth redoing eventually); ok = passes. Similarity to another voice is
// NOT a defect — overlaps are shown separately.
function voiceState(s) {
    if (!s.voice_enrolled) return { label: "No voice", tone: "orange" }
    const c = s.voice_check
    if (!c) return { label: "Voice ✓", tone: "neutral" } // not yet checked
    const broken =
        (c.net_speech_seconds ?? 0) < 5 ||
        (c.self_similarity != null && c.self_similarity < 0.45)
    if (broken) return { label: "Voice: weak", tone: "orange" }
    if (c.ok === false) return { label: "Voice: short", tone: "neutral" }
    return { label: "Voice ✓", tone: "teal" }
}

function enrollmentNeedsAttention(s) {
    return (
        !s.voice_enrolled ||
        !s.face_enrolled ||
        voiceState(s).label === "Voice: weak"
    )
}

// Student roster with participation stats. Every signed-in user can view it;
// the server scopes regular users to students seen in their own sessions.
// Add / sync / edit / delete are admin-only.
function StudentsComponent(props) {
    const me = props.userdata
    const navigate = useNavigate()
    const canManage = isManager(me)

    const [students, setStudents] = useState(null)
    const [search, setSearch] = useState("")
    const [filter, setFilter] = useState("all") // all | enrolled | not | attention
    const [sort, setSort] = useState({ key: "last_active", dir: "desc" })
    const [currentForm, setCurrentForm] = useState("")
    const [status, setStatus] = useState("")
    const [statusTitle, setStatusTitle] = useState("")
    const [target, setTarget] = useState(null) // student a dialog acts on
    const [activity, setActivity] = useState(null) // drill-down payload
    const [syncEnabled, setSyncEnabled] = useState(false)
    // Bulk selection (admins): toggled from the row's index/select cell.
    const [selected, setSelected] = useState(() => new Set())
    // username -> [{other, similarity}] for voices that sound alike.
    const [voiceOverlaps, setVoiceOverlaps] = useState({})

    const toggleSelected = (id) =>
        setSelected((prev) => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    const clearSelected = () => setSelected(new Set())

    const loadStudents = async () => {
        try {
            const response = await new AuthService().getStudentsOverview()
            setStudents(response.status === 200 ? await response.json() : [])
        } catch {
            setStudents([])
        }
        // Which enrolled voices sound alike (similar voices may enroll; the
        // overlap is surfaced so attribution can be interpreted).
        try {
            const r = await new ApiService().httpRequestCall(
                "api/v1/students/voice_overlaps", "GET", {})
            if (r.status === 200) {
                const d = await r.json()
                const map = {}
                for (const p of d.pairs || []) {
                    ;(map[p.a] = map[p.a] || []).push({ other: p.b, similarity: p.similarity })
                    ;(map[p.b] = map[p.b] || []).push({ other: p.a, similarity: p.similarity })
                }
                setVoiceOverlaps(map)
            }
        } catch { /* overlap info is best-effort */ }
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
        // Enrollment health: how many enrolled prints need re-recording, and
        // how many students are in a confusable-voice pair.
        const attention = students.filter((s) => enrollmentNeedsAttention(s)).length
        const confusableUsers = new Set()
        for (const pair of voiceOverlaps.pairs || []) {
            confusableUsers.add(pair.a)
            confusableUsers.add(pair.b)
        }
        return {
            total: students.length, enrolled, active, attention,
            confusable: confusableUsers.size,
            confusablePairs: (voiceOverlaps.pairs || []).length,
        }
    }, [students, voiceOverlaps])

    const visible = useMemo(() => {
        if (students === null) return null
        const q = search.trim().toLowerCase()
        let list = students
        if (filter === "enrolled")
            list = list.filter((s) => s.biometric_captured === "yes")
        if (filter === "not")
            list = list.filter((s) => s.biometric_captured !== "yes")
        if (filter === "attention")
            list = list.filter((s) => enrollmentNeedsAttention(s))
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

    const mergeStudent = async (targetId) => {
        if (!targetId) {
            setStatus("Pick the student to merge into.")
            return
        }
        setCurrentForm("Loading")
        try {
            const response = await new AuthService().mergeStudents(
                target.id,
                +targetId,
            )
            if (response.status === 200) {
                const body = await response.json()
                await loadStudents()
                showStatus(
                    "Students merged",
                    `${target.username} was merged into ${body.target.username}. ` +
                        `${body.moved.speakers} session ${body.moved.speakers === 1 ? "appearance" : "appearances"} moved.`,
                )
            } else {
                let message = `${target.username} could not be merged.`
                try {
                    const err = await response.json()
                    if (err["message"]) message = err["message"]
                } catch {
                    /* non-JSON error body */
                }
                showStatus("Failed to merge", message)
            }
        } catch {
            showStatus("Failed to merge", "The server could not be reached.")
        }
    }

    // Merge every selected duplicate into the chosen survivor, one call per
    // duplicate (the endpoint is single-pair).
    const bulkMerge = async (survivorId) => {
        if (!survivorId) {
            setStatus("Pick which student to keep.")
            return
        }
        const dups = [...selected].filter((id) => id !== +survivorId)
        setCurrentForm("Loading")
        let movedTotal = 0
        let failed = 0
        for (const dupId of dups) {
            try {
                const response = await new AuthService().mergeStudents(
                    dupId,
                    +survivorId,
                )
                if (response.status === 200) {
                    const body = await response.json()
                    movedTotal += body.moved.speakers || 0
                } else {
                    failed++
                }
            } catch {
                failed++
            }
        }
        clearSelected()
        await loadStudents()
        showStatus(
            failed ? "Merge partly failed" : "Students merged",
            `${dups.length - failed} ${dups.length - failed === 1 ? "profile" : "profiles"} merged, ` +
                `${movedTotal} session ${movedTotal === 1 ? "appearance" : "appearances"} moved.` +
                (failed ? ` ${failed} failed.` : ""),
        )
    }

    const bulkDelete = async () => {
        const ids = [...selected]
        setCurrentForm("Loading")
        let failed = 0
        for (const id of ids) {
            try {
                const response = await new AuthService().deleteStudent(id)
                if (response.status !== 200) failed++
            } catch {
                failed++
            }
        }
        clearSelected()
        await loadStudents()
        showStatus(
            failed ? "Delete partly failed" : "Students deleted",
            `${ids.length - failed} ${ids.length - failed === 1 ? "profile" : "profiles"} deleted.` +
                (failed ? ` ${failed} failed.` : ""),
        )
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

    // Sign-up refuses an existing username once biometric_captured is "yes",
    // so a broken enrollment is otherwise stuck. Resetting the flag re-opens
    // the same-username sign-up path (old files are replaced on re-record).
    const allowReenrollment = async () => {
        try {
            const response = await new ApiService().httpRequestCall(
                "api/v1/student/updatestudent",
                "POST",
                { id: target.id, biometric_captured: "no" },
            )
            if (response.status === 200) {
                await loadStudents()
                showStatus(
                    "Re-enrollment enabled",
                    `${target.username} can now redo the sign-up recording with the same username.`,
                )
            } else {
                showStatus("Failed", "Could not enable re-enrollment.")
            }
        } catch {
            showStatus("Failed", "The server could not be reached.")
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
            "First name,Last name,Username,Voice,Face,Sessions,Last active,Created",
            ...(visible || []).map((s) =>
                [
                    esc(s.firstname),
                    esc(s.lastname),
                    esc(s.username),
                    esc(voiceState(s).label),
                    s.face_enrolled ? "yes" : "no",
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
                                <button
                                    type="button"
                                    onClick={() =>
                                        setFilter(
                                            filter === "attention"
                                                ? "all"
                                                : "attention",
                                        )
                                    }
                                    className={
                                        "flex-1 rounded-xl border p-4 text-left transition " +
                                        (stats.attention
                                            ? "border-tiilt-orange/40 bg-tiilt-orange/10 hover:border-tiilt-orange"
                                            : "border-tiilt-line bg-white hover:border-tiilt")
                                    }
                                    title={
                                        stats.attention
                                            ? "Filter to enrollments needing re-recording"
                                            : "All enrollments look healthy"
                                    }
                                >
                                    <div className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                        Enrollment health
                                    </div>
                                    <div
                                        className={
                                            "mt-1 text-2xl font-bold " +
                                            (stats.attention
                                                ? "text-tiilt-orange-text"
                                                : "text-tiilt-teal-text")
                                        }
                                    >
                                        {stats.attention
                                            ? `${stats.attention} need attention`
                                            : "All healthy"}
                                    </div>
                                    <div className="mt-1 text-xs text-tiilt-muted">
                                        {stats.confusable > 0
                                            ? `${stats.confusable} in ${stats.confusablePairs} confusable pair${stats.confusablePairs === 1 ? "" : "s"}`
                                            : "no voice overlaps"}
                                    </div>
                                </button>
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
                                {filterChip("attention", "Needs attention")}
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

                        {selected.size > 0 ? (
                            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-tiilt/40 bg-tiilt-soft/60 px-4 py-2.5">
                                <span className="text-sm font-semibold text-tiilt-ink">
                                    {selected.size} selected
                                </span>
                                <button
                                    className={btnSecondary + " disabled:cursor-not-allowed disabled:opacity-50"}
                                    disabled={selected.size < 2}
                                    title={
                                        selected.size < 2
                                            ? "Select at least two students to merge"
                                            : "Merge the selected profiles into one"
                                    }
                                    onClick={() =>
                                        setCurrentForm("MergeSelected")
                                    }
                                >
                                    Merge…
                                </button>
                                <button
                                    className={btnSecondary + " text-tiilt-danger hover:border-tiilt-danger hover:bg-tiilt-danger-soft"}
                                    onClick={() =>
                                        setCurrentForm("ConfirmBulkDelete")
                                    }
                                >
                                    Delete
                                </button>
                                <button
                                    className="ml-auto cursor-pointer text-sm font-semibold text-tiilt-muted transition hover:text-tiilt"
                                    onClick={clearSelected}
                                >
                                    Clear
                                </button>
                            </div>
                        ) : null}

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
                                            {canManage ? (
                                                <th className="sticky top-0 bg-tiilt-ground py-2.5 pr-1 pl-3 text-center">
                                                    <input
                                                        type="checkbox"
                                                        title="Select all displayed students"
                                                        aria-label="Select all displayed students"
                                                        className="h-4 w-4 cursor-pointer accent-tiilt"
                                                        checked={
                                                            (visible || []).length > 0 &&
                                                            visible.every((s) => selected.has(s.id))
                                                        }
                                                        onChange={() =>
                                                            setSelected((prev) => {
                                                                const all = visible.every((s) => prev.has(s.id))
                                                                const next = new Set(prev)
                                                                visible.forEach((s) =>
                                                                    all ? next.delete(s.id) : next.add(s.id),
                                                                )
                                                                return next
                                                            })
                                                        }
                                                    />
                                                </th>
                                            ) : null}
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
                                        {visible.map((s, rowIndex) => (
                                            <tr
                                                key={s.id}
                                                onClick={() => openActivity(s)}
                                                title={`View ${s.firstname}'s session history`}
                                                className="cursor-pointer border-t border-tiilt-line bg-white transition first:border-t-0 hover:bg-tiilt-soft/50"
                                            >
                                                {canManage ? (
                                                    <td
                                                        className="py-2.5 pr-1 pl-3 text-center"
                                                        onClick={(e) => e.stopPropagation()}
                                                    >
                                                        <button
                                                            onClick={() => toggleSelected(s.id)}
                                                            role="checkbox"
                                                            aria-checked={selected.has(s.id)}
                                                            aria-label={`Select ${s.firstname} ${s.lastname}`}
                                                            title={selected.has(s.id) ? "Deselect" : "Select for bulk actions"}
                                                            className={
                                                                "mx-auto flex h-7 w-8 flex-none cursor-pointer items-center justify-center rounded-md font-ahamono text-xs tabular-nums transition " +
                                                                (selected.has(s.id)
                                                                    ? "bg-tiilt font-bold text-white ring-2 ring-tiilt/40"
                                                                    : "text-tiilt-muted hover:bg-tiilt-soft hover:text-tiilt")
                                                            }
                                                        >
                                                            {selected.has(s.id) ? "\u2713" : rowIndex + 1}
                                                        </button>
                                                    </td>
                                                ) : null}
                                                <td className="px-4 py-2.5">
                                                    <span className="min-w-0">
                                                        <span className="block truncate font-semibold text-tiilt-ink">
                                                            {s.firstname}{" "}
                                                            {s.lastname}
                                                        </span>
                                                        <span className="block truncate font-ahamono text-xs text-tiilt-muted">
                                                            {s.username}
                                                        </span>
                                                    </span>
                                                </td>
                                                <td
                                                    className="px-4 py-2.5"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        setTarget(s)
                                                        setCurrentForm("Enrollment")
                                                    }}
                                                    title="View enrollment details"
                                                >
                                                    <span className="flex flex-wrap gap-1">
                                                        <StatusPill
                                                            tone={voiceState(s).tone}
                                                            dot
                                                        >
                                                            {voiceState(s).label}
                                                        </StatusPill>
                                                        <StatusPill
                                                            tone={s.face_enrolled ? "teal" : "orange"}
                                                            dot
                                                        >
                                                            {s.face_enrolled ? "Face ✓" : "No face"}
                                                        </StatusPill>
                                                        {(voiceOverlaps[s.username] || []).length > 0 ? (
                                                            <StatusPill
                                                                tone="brand"
                                                                title={
                                                                    "Voice sounds similar to: " +
                                                                    voiceOverlaps[s.username]
                                                                        .map((o) => `${o.other} (${Math.round(o.similarity * 100)}%)`)
                                                                        .join(", ")
                                                                }
                                                            >
                                                                ≈ {voiceOverlaps[s.username].length}{" "}
                                                                {voiceOverlaps[s.username].length === 1 ? "voice" : "voices"}
                                                            </StatusPill>
                                                        ) : null}
                                                    </span>
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
                                                                    "Enrollment",
                                                                )
                                                            }}
                                                        >
                                                            Enrollment details
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
                                                                className={
                                                                    contextStyle[
                                                                        "menu-item"
                                                                    ]
                                                                }
                                                                onClick={() => {
                                                                    setTarget(s)
                                                                    setCurrentForm(
                                                                        "MergeStudent",
                                                                    )
                                                                }}
                                                            >
                                                                Merge into…
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
                {currentForm === "Enrollment" && target ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Enrollment — {target.firstname} {target.lastname}
                        </div>
                        <div className="mb-1 text-sm font-semibold text-tiilt-ink">
                            Voice fingerprint
                        </div>
                        {target.voice_enrolled ? (
                            <>
                                <audio
                                    controls
                                    preload="none"
                                    className="mb-3 w-full"
                                    src={`/api/v1/students/${target.id}/fingerprint_audio`}
                                />
                                {target.voice_check ? (
                                    <div className="mb-3 flex flex-col gap-1.5 rounded-lg bg-tiilt-ground/60 px-3 py-2 text-xs text-tiilt-ink">
                                        <div className="flex items-center justify-between gap-3">
                                            <span>Clear speech in the recording</span>
                                            <span className={"font-ahamono font-semibold " + ((target.voice_check.net_speech_seconds ?? 0) >= 12 ? "text-tiilt-teal-text" : "text-tiilt-orange-text")}>
                                                {target.voice_check.net_speech_seconds ?? "?"}s
                                                <span className="font-normal text-tiilt-muted"> / 12s needed</span>
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between gap-3" title="How well the two halves of the recording match each other. Low values mean noise or too little speech.">
                                            <span>Matches itself</span>
                                            <span className={"font-ahamono font-semibold " + ((target.voice_check.self_similarity ?? 0) >= 0.45 ? "text-tiilt-teal-text" : "text-tiilt-orange-text")}>
                                                {target.voice_check.self_similarity ?? "—"}
                                                <span className="font-normal text-tiilt-muted"> / 0.45 needed</span>
                                            </span>
                                        </div>
                                        <div className="flex items-center justify-between gap-3" title="Similarity to the closest OTHER enrolled voice. High values mean this student's speech can be confused with someone else's.">
                                            <span>Confusable with another voice</span>
                                            <span className={"font-ahamono font-semibold " + ((target.voice_check.nearest_other_similarity ?? 0) < 0.5 ? "text-tiilt-teal-text" : "text-tiilt-orange-text")}>
                                                {target.voice_check.nearest_other_similarity ?? "—"}
                                                <span className="font-normal text-tiilt-muted"> (0.50 = too close)</span>
                                            </span>
                                        </div>
                                        {target.voice_check.ok === false ? (
                                            <div className="mt-1 rounded-md bg-tiilt-orange/15 px-2.5 py-1.5 leading-relaxed text-tiilt-orange-text">
                                                {target.voice_check.message ||
                                                    "This recording failed the quality check."}
                                            </div>
                                        ) : null}
                                    </div>
                                ) : (
                                    <div className="mb-3 text-xs text-tiilt-muted">
                                        No quality report yet for this recording.
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="mb-3 rounded-md bg-tiilt-orange/15 px-3 py-2 text-xs text-tiilt-orange-text">
                                No voice recording on file — this student's speech
                                can only be attributed by diarization clustering.
                            </div>
                        )}
                        {(voiceOverlaps[target.username] || []).length > 0 ? (
                            <div className="mb-3">
                                <div className="mb-1 text-sm font-semibold text-tiilt-ink">
                                    Sounds similar to
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {voiceOverlaps[target.username].map((o) => (
                                        <span
                                            key={o.other}
                                            className="inline-flex items-center gap-1 rounded-full bg-tiilt-soft px-2.5 py-1 text-xs font-semibold text-tiilt"
                                        >
                                            {o.other}
                                            <span className="font-ahamono font-normal text-tiilt-muted">
                                                {Math.round(o.similarity * 100)}%
                                            </span>
                                        </span>
                                    ))}
                                </div>
                                <div className="mt-1 text-[11px] leading-relaxed text-tiilt-muted">
                                    These voices can be confused with each other during
                                    attribution — worth keeping in mind when reading
                                    per-student metrics for groups containing both.
                                </div>
                            </div>
                        ) : null}
                        <div className="mb-1 text-sm font-semibold text-tiilt-ink">
                            Face enrollment
                        </div>
                        <div className="mb-3 text-xs text-tiilt-muted">
                            {target.face_enrolled
                                ? "A face embedding is on file. If this student is regularly reported as an unmatched face in video analysis, the embedding is poor — re-enrollment fixes it."
                                : "No face embedding on file — this student cannot be identified in video."}
                        </div>
                        <div className="mb-3 rounded-lg bg-tiilt-soft px-3 py-2 text-xs leading-relaxed text-tiilt">
                            Students can re-enroll themselves: they redo the
                            sign-up recording with the same username and the
                            same first/last name. New recordings are
                            quality-checked automatically before being
                            accepted. If their name was registered with a
                            different spelling, use the button below to bypass
                            the name check once.
                        </div>
                        {target.biometric_captured === "yes" ? (
                            <button
                                className={dlgPrimary}
                                onClick={allowReenrollment}
                            >
                                Allow re-enrollment (bypass name check)
                            </button>
                        ) : null}
                        <button className={dlgCancel} onClick={closeDialog}>
                            Close
                        </button>
                    </div>
                ) : null}

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

                {currentForm === "MergeSelected" && selected.size > 1 ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Merge {selected.size} students
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            Pick which profile to keep. Everything from the
                            others — session appearances, metrics, AI
                            feedback, survey responses — moves to it, and
                            their profiles are deleted. This can't be undone.
                        </div>
                        <div
                            role="radiogroup"
                            aria-label="Profile to keep"
                            className="flex max-h-60 flex-col gap-1 overflow-y-auto"
                        >
                            {(students || [])
                                .filter((s) => selected.has(s.id))
                                .map((s) => (
                                    <label
                                        key={s.id}
                                        className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-tiilt-line px-3 py-2 transition hover:border-tiilt hover:bg-tiilt-soft/50"
                                    >
                                        <input
                                            type="radio"
                                            name="mergeSurvivor"
                                            value={s.id}
                                            className="h-4 w-4 cursor-pointer accent-tiilt"
                                        />
                                        <span className="text-sm font-semibold text-tiilt-ink">
                                            {s.firstname} {s.lastname}
                                        </span>
                                        <span className="font-ahamono text-xs text-tiilt-muted">
                                            {s.username} ·{" "}
                                            {s.session_count || 0} sessions
                                        </span>
                                    </label>
                                ))}
                        </div>
                        {status ? (
                            <div className={dlgError}>{status}</div>
                        ) : null}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                bulkMerge(
                                    document.querySelector(
                                        'input[name="mergeSurvivor"]:checked',
                                    )?.value,
                                )
                            }
                        >
                            Merge into selected
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "ConfirmBulkDelete" && selected.size > 0 ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Delete {selected.size}{" "}
                            {selected.size === 1 ? "student" : "students"}?
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            This removes the selected profiles and their
                            enrolled biometrics. This can't be undone.
                        </div>
                        <button className={dlgDanger} onClick={bulkDelete}>
                            Delete {selected.size}{" "}
                            {selected.size === 1 ? "student" : "students"}
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
                        </button>
                    </div>
                ) : null}

                {currentForm === "MergeStudent" && target ? (
                    <div className={dlgBody}>
                        <div className={dlgHeading}>
                            Merge {target.username}
                        </div>
                        <div className="text-sm text-tiilt-muted">
                            All of {target.firstname} {target.lastname}'s
                            session appearances, metrics, AI feedback, and
                            survey responses move to the student you pick,
                            and the {target.username} profile is deleted.
                            This can't be undone.
                        </div>
                        <label htmlFor="mergeTarget" className={dlgLabel}>
                            Merge into
                        </label>
                        <select
                            id="mergeTarget"
                            className={dlgSelect}
                            defaultValue=""
                        >
                            <option value="" disabled>
                                Choose a student…
                            </option>
                            {(students || [])
                                .filter((s) => s.id !== target.id)
                                .sort((a, b) =>
                                    `${a.lastname}${a.firstname}`.localeCompare(
                                        `${b.lastname}${b.firstname}`,
                                    ),
                                )
                                .map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {s.firstname} {s.lastname} (
                                        {s.username})
                                    </option>
                                ))}
                        </select>
                        {status ? (
                            <div className={dlgError}>{status}</div>
                        ) : null}
                        <button
                            className={dlgPrimary}
                            onClick={() =>
                                mergeStudent(
                                    document.getElementById("mergeTarget")
                                        .value,
                                )
                            }
                        >
                            Merge students
                        </button>
                        <button className={dlgCancel} onClick={closeDialog}>
                            Cancel
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
