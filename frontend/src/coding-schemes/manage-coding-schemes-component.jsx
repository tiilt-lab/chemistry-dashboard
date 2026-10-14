import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { CodingSchemeService } from "../services/coding-scheme-service"
import { AppContextMenu } from "../components/context-menu/context-menu-component"
import { SkeletonRows } from "../components/skeleton"
import { EmptyState } from "../components/empty-state"
import { StatusPill } from "../components/status-pill"
import { btnPrimary } from "../components/dialog-styles"
import { pageShell, wideCard, cardFooter } from "../components/layout-styles"
import { DialogBoxTwoOption } from "../dialog/dialog-component"
import { Appheader } from "../header/header-component"
import { LibraryTabs } from "../components/library-tabs"
import style from "../components/library-dialog.module.css"
import style2 from "../components/context-menu/context-menu.module.css"

// Coding schemes: what the utterance coder codes for. The built-in
// negotiation scheme is listed first and opens read-only (duplicate it to
// change it); the caller's own schemes open in the editor.
function ManageCodingSchemesComponent() {
    const navigate = useNavigate()
    const [svc] = useState(() => new CodingSchemeService())
    const [schemes, setSchemes] = useState(null)
    const [error, setError] = useState(null)
    const [toDelete, setToDelete] = useState(null)

    useEffect(() => {
        let alive = true
        svc.list().then(({ status, body }) => {
            if (!alive) return
            if (status === 200 && Array.isArray(body)) setSchemes(body)
            else setError(`Could not load coding schemes (HTTP ${status}).`)
        })
        return () => {
            alive = false
        }
    }, [svc])

    const confirmDelete = () => {
        const target = toDelete
        setToDelete(null)
        if (!target) return
        svc.delete(target.id).then(({ status }) => {
            if (status === 200) setSchemes((list) => (list || []).filter((s) => s.id !== target.id))
            else setError(`Could not delete "${target.name}" (HTTP ${status}).`)
        })
    }

    return (
        <>
            <div role="main" className="main-container">
                <Appheader title={"Library"} leftText={false} rightText={""} nav={() => navigate("/home")} />
                <LibraryTabs />
                <div className={pageShell}>
                    <div className={wideCard}>
                        <div className="relative min-h-0 w-full grow">
                            <div className="mx-auto w-full max-w-4xl px-4 py-6">
                                <p className="mb-4 text-sm text-tiilt-muted">
                                    A coding scheme says what the local model codes every utterance
                                    for: its dimensions and the codes in each. Pick one when you start
                                    a session; the results roll up per team and per speaker on the pod
                                    page.
                                </p>
                                {error ? <div className="mb-3 text-sm text-tiilt-danger">{error}</div> : null}
                                {schemes === null ? <SkeletonRows rows={3} /> : null}
                                {schemes && schemes.length === 0 ? (
                                    <EmptyState title="No coding schemes" subtitle="Make one below." />
                                ) : null}
                                <ul className="flex flex-col gap-2">
                                    {(schemes || []).map((s) => (
                                        <li
                                            key={s.ref}
                                            className="flex items-center gap-3 rounded-xl border border-tiilt-line bg-white px-4 py-3 transition hover:border-tiilt hover:shadow-card-hover"
                                        >
                                            <button
                                                onClick={() => navigate("/coding-schemes/" + encodeURIComponent(s.ref))}
                                                className="min-w-0 grow cursor-pointer text-left"
                                            >
                                                <span className="flex items-center gap-2">
                                                    <span className="truncate text-base font-semibold text-tiilt-ink">{s.name}</span>
                                                    {s.builtin ? (
                                                        <StatusPill tone="neutral" className="text-[10px]">
                                                            Built in
                                                        </StatusPill>
                                                    ) : null}
                                                    <span className="ml-auto flex-none text-xs text-tiilt-muted">
                                                        {s.dimension_count} {s.dimension_count === 1 ? "dimension" : "dimensions"}
                                                    </span>
                                                </span>
                                                <span className="mt-0.5 block truncate text-sm text-tiilt-muted">
                                                    {s.description || "No description."}
                                                </span>
                                            </button>
                                            {!s.builtin ? (
                                                <div className="flex-none">
                                                    <AppContextMenu label={`Options for ${s.name}`}>
                                                        <button
                                                            role="menuitem"
                                                            className={`${style2["menu-item"]} ${style2["red"]}`}
                                                            onClick={() => setToDelete(s)}
                                                        >
                                                            Delete
                                                        </button>
                                                    </AppContextMenu>
                                                </div>
                                            ) : null}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                        <div className={cardFooter}>
                            <button
                                className={btnPrimary + " h-11 w-full max-w-55 cursor-pointer"}
                                onClick={() => navigate("/coding-schemes/new")}
                            >
                                New coding scheme
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            <DialogBoxTwoOption
                show={!!toDelete}
                itsclass={style["dialog-window"]}
                heading={"Delete coding scheme"}
                body={
                    "Delete this scheme? Sessions that already used it keep their coded results; a new run on them would use the built-in negotiation scheme."
                }
                deletebuttonaction={confirmDelete}
                cancelbuttonaction={() => setToDelete(null)}
            />
        </>
    )
}

export { ManageCodingSchemesComponent }
