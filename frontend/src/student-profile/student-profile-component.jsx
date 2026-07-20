import { useState, useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Appheader } from "../header/header-component"
import { AppSpinner } from "../spinner/spinner-component"
import { DataTable } from "../components/data-table"
import { StatusPill } from "../components/status-pill"
import { AuthService } from "../services/auth-service"
import { StudentLongitudinalPanel } from "../components/student-longitudinal/student-longitudinal-panel"
import { VoiceQualityCard, voiceState } from "../components/voice-quality"

// "2026-06-18 14:35:58 UTC" -> "Jun 18, 2026"
const fmtDate = (s) => {
    if (!s) return "—"
    const d = new Date(s.replace(" UTC", "").replace(" ", "T") + "Z")
    return isNaN(d)
        ? "—"
        : d.toLocaleDateString(undefined, {
              year: "numeric",
              month: "short",
              day: "numeric",
          })
}

// The student-centric page: who this person is, whether their biometrics are
// usable, how their participation has moved across the term, and every
// session they appeared in. Everything about a *person over time* lives here;
// session dashboards stay about *one discussion*.
function StudentProfileComponent(props) {
    const { studentId } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        let alive = true
        setData(null)
        setError(false)
        new AuthService()
            .getStudentActivity(studentId)
            .then((r) => (r.status === 200 ? r.json() : Promise.reject()))
            .then((d) => alive && setData(d))
            .catch(() => alive && setError(true))
        return () => {
            alive = false
        }
    }, [studentId])

    const student = data?.student
    const sessions = data?.sessions || []
    const vs = student ? voiceState(student) : null

    return (
        <div role="main" className="main-container">
            <Appheader
                title={
                    student
                        ? `${student.firstname} ${student.lastname}`
                        : "Student"
                }
                nav={() => navigate("/students")}
                escToBack
            />
            <div className="relative min-h-0 w-full grow overflow-y-auto bg-tiilt-ground/60">
                <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-8">
                    {error ? (
                        <div className="rounded-lg bg-tiilt-danger-soft px-4 py-3 text-sm text-tiilt-danger">
                            Couldn't load this student. They may have been
                            removed, or the server is unreachable.
                        </div>
                    ) : !data ? (
                        <div className="flex justify-center py-16">
                            <AppSpinner />
                        </div>
                    ) : (
                        <>
                            {/* identity + enrollment at a glance */}
                            <div className="rounded-xl border border-tiilt-line bg-white p-5">
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                                    <h2 className="text-xl font-semibold text-tiilt-ink">
                                        {student.firstname} {student.lastname}
                                    </h2>
                                    <span className="font-ahamono text-sm text-tiilt-muted">
                                        {student.username}
                                    </span>
                                    <div className="ml-auto flex flex-wrap gap-1.5">
                                        <StatusPill tone={vs.tone}>
                                            {vs.label}
                                        </StatusPill>
                                        <StatusPill
                                            tone={
                                                student.face_enrolled
                                                    ? "teal"
                                                    : "orange"
                                            }
                                        >
                                            {student.face_enrolled
                                                ? "Face ✓"
                                                : "No face"}
                                        </StatusPill>
                                    </div>
                                </div>
                                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-tiilt-muted">
                                    <span>
                                        {sessions.length}{" "}
                                        {sessions.length === 1
                                            ? "session"
                                            : "sessions"}
                                    </span>
                                    {data.llm_reports > 0 ? (
                                        <span>
                                            {data.llm_reports} LLM feedback{" "}
                                            {data.llm_reports === 1
                                                ? "report"
                                                : "reports"}
                                        </span>
                                    ) : null}
                                    <span>
                                        Enrolled {fmtDate(student.creation_date)}
                                    </span>
                                </div>
                            </div>

                            {/* voice fingerprint quality */}
                            <div className="rounded-xl border border-tiilt-line bg-white p-5">
                                <div className="mb-2 text-sm font-semibold text-tiilt-ink">
                                    Voice fingerprint
                                </div>
                                <VoiceQualityCard student={student} />
                                <div className="text-xs text-tiilt-muted">
                                    {student.face_enrolled
                                        ? "A face embedding is also on file."
                                        : "No face embedding on file — this student cannot be identified in video."}
                                </div>
                            </div>

                            {/* cross-session participation — the longitudinal
                                view's real home */}
                            <div className="rounded-xl border border-tiilt-line bg-white p-5">
                                <StudentLongitudinalPanel
                                    username={student.username}
                                />
                            </div>

                            {/* every session they appeared in */}
                            <div className="rounded-xl border border-tiilt-line bg-white p-5">
                                <div className="mb-3 text-sm font-semibold text-tiilt-ink">
                                    Sessions
                                </div>
                                {sessions.length === 0 ? (
                                    <div className="rounded-lg bg-tiilt-soft/60 px-4 py-6 text-center text-sm text-tiilt-muted">
                                        No session participation yet — they'll
                                        appear here once they enroll a
                                        fingerprint in a session.
                                    </div>
                                ) : (
                                    <DataTable
                                        columns={["Session", "Date", "Group", ""]}
                                        rows={sessions.map((s) => [
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
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}

export { StudentProfileComponent }
