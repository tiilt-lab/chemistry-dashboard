import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { CodingSchemeService } from "../services/coding-scheme-service"
import { btnPrimary, btnSecondary, btnSecondarySm, btnDangerOutlineSm, dlgError } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { Appheader } from "../header/header-component"
import { LibraryTabs } from "../components/library-tabs"
import { InlineSpinner } from "../components/inline-spinner"
import { emptyScheme, emptyDimension, emptyCode, toForm, toApi, formProblem, slugify } from "./scheme-form"

const input =
    "h-9 w-full rounded-lg border border-tiilt-line bg-white px-2 text-sm text-tiilt-ink outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 disabled:bg-tiilt-ground"
const area =
    "w-full rounded-lg border border-tiilt-line bg-white px-2 py-1.5 text-sm text-tiilt-ink outline-none focus-visible:border-tiilt focus-visible:ring-[3px] focus-visible:ring-tiilt/30 disabled:bg-tiilt-ground"
const label = "mb-1 block text-xs text-tiilt-muted"
const title = "text-sm font-semibold text-tiilt-ink"

// One coding scheme: the editor for the caller's own, a read-only view of a
// built-in (with "Duplicate" into a new scheme). Everything is plain form
// state (scheme-form.js); the server validates on save and says what is
// wrong in its own words.
function CodingSchemeEditorComponent() {
    const navigate = useNavigate()
    const { ref } = useParams()
    const [svc] = useState(() => new CodingSchemeService())
    const isNew = !ref || ref === "new"
    const [form, setForm] = useState(emptyScheme)
    const [loaded, setLoaded] = useState(isNew)
    const [builtin, setBuiltin] = useState(false)
    const [schemeId, setSchemeId] = useState(null)
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)
    const [saved, setSaved] = useState(false)

    useEffect(() => {
        if (isNew) return undefined
        let alive = true
        svc.get(decodeURIComponent(ref)).then(({ status, body }) => {
            if (!alive) return
            if (status === 200 && body) {
                setForm(toForm(body))
                setBuiltin(body.builtin === true)
                setSchemeId(body.id || null)
                setLoaded(true)
            } else setError(`Could not load this scheme (HTTP ${status}).`)
        })
        return () => {
            alive = false
        }
    }, [svc, ref, isNew])

    const readOnly = builtin
    const set = (patch) => setForm((f) => ({ ...f, ...patch }))
    const setDim = (i, patch) =>
        setForm((f) => ({ ...f, dimensions: f.dimensions.map((d, j) => (j === i ? { ...d, ...patch } : d)) }))
    const setCode = (i, k, patch) =>
        setDim(i, { codes: form.dimensions[i].codes.map((c, m) => (m === k ? { ...c, ...patch } : c)) })

    const startFromBuiltin = () => {
        setBusy(true)
        svc.get("builtin:negotiation").then(({ status, body }) => {
            setBusy(false)
            if (status === 200 && body) {
                const f = toForm(body)
                setForm({ ...f, name: "" })
            }
        })
    }

    const duplicate = () => {
        setForm((f) => ({ ...f, name: `${f.name} (copy)`.slice(0, 64) }))
        setBuiltin(false)
        setSchemeId(null)
        navigate("/coding-schemes/new", { replace: true })
    }

    const save = () => {
        const problem = formProblem(form)
        if (problem) {
            setError(problem)
            return
        }
        setBusy(true)
        setError(null)
        setSaved(false)
        const payload = toApi(form)
        const request = schemeId ? svc.update(schemeId, payload) : svc.create(payload)
        request
            .then(({ status, body }) => {
                if (status === 200 && body) {
                    setSaved(true)
                    if (!schemeId) navigate("/coding-schemes/" + encodeURIComponent(body.ref), { replace: true })
                    else setForm(toForm(body))
                } else setError((body && body.message) || `Could not save (HTTP ${status}).`)
            })
            .catch(() => setError("Could not save (network error)."))
            .finally(() => setBusy(false))
    }

    return (
        <div role="main" className="main-container">
            <Appheader title={"Library"} leftText={false} rightText={""} nav={() => navigate("/coding-schemes")} />
            <LibraryTabs />
            <div className={pageShell}>
                <div className={formCard}>
                    <div className="relative min-h-0 w-full grow overflow-y-auto">
                        <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
                            {!loaded && !error ? <div className="text-sm text-tiilt-muted">Loading…</div> : null}
                            {loaded ? (
                                <>
                                    {readOnly ? (
                                        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-tiilt-ground/50 px-3 py-2 text-xs text-tiilt-muted">
                                            <span>This scheme is built in and cannot be changed. Duplicate it to make your own version.</span>
                                            <button className={btnSecondarySm} onClick={duplicate}>
                                                Duplicate as my own
                                            </button>
                                        </div>
                                    ) : null}
                                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                                        <div>
                                            <label htmlFor="schemeName" className={label}>
                                                Name
                                            </label>
                                            <input id="schemeName" className={input} maxLength={64} disabled={readOnly}
                                                value={form.name} onChange={(e) => set({ name: e.target.value })} placeholder="e.g. Negotiation moves" />
                                        </div>
                                        <div>
                                            <label htmlFor="schemeDescription" className={label}>
                                                Description
                                            </label>
                                            <input id="schemeDescription" className={input} maxLength={500} disabled={readOnly}
                                                value={form.description} onChange={(e) => set({ description: e.target.value })} placeholder="What this scheme captures" />
                                        </div>
                                    </div>
                                    <div>
                                        <label htmlFor="schemeContext" className={label}>
                                            Context the coder should know (one fact per line, optional)
                                        </label>
                                        <textarea id="schemeContext" className={area} rows={3} disabled={readOnly}
                                            value={form.context} onChange={(e) => set({ context: e.target.value })}
                                            placeholder="Names, numbers and background that come up in the discussion, so the coder understands references." />
                                    </div>
                                    {isNew && form.dimensions.length === 1 && !form.dimensions[0].label ? (
                                        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-tiilt-line px-3 py-2 text-xs text-tiilt-muted">
                                            <span>Starting from scratch, or from the built-in negotiation scheme?</span>
                                            <button className={btnSecondarySm} onClick={startFromBuiltin} disabled={busy}>
                                                Start from the negotiation scheme
                                            </button>
                                        </div>
                                    ) : null}

                                    <div className="flex flex-col gap-4">
                                        {form.dimensions.map((d, i) => (
                                            <div key={d.id} className="rounded-xl border border-tiilt-line bg-white">
                                                <div className="flex items-center justify-between gap-3 border-b border-tiilt-line bg-tiilt-ground/40 px-4 py-2">
                                                    <span className={title}>Dimension {i + 1}</span>
                                                    {!readOnly ? (
                                                        <button className={btnDangerOutlineSm} onClick={() => set({ dimensions: form.dimensions.filter((_, j) => j !== i) })}>
                                                            Remove dimension
                                                        </button>
                                                    ) : null}
                                                </div>
                                                <div className="flex flex-col gap-3 px-4 py-3">
                                                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_10rem_14rem]">
                                                        <div>
                                                            <label className={label}>Label</label>
                                                            <input className={input} maxLength={40} disabled={readOnly} value={d.label}
                                                                onChange={(e) => setDim(i, { label: e.target.value })} placeholder="e.g. Emotion" />
                                                        </div>
                                                        <div>
                                                            <label className={label}>Key</label>
                                                            <input className={input + " font-ahamono"} maxLength={24} disabled={readOnly}
                                                                value={d.key} placeholder={slugify(d.label) || "auto"}
                                                                onChange={(e) => setDim(i, { key: e.target.value })} />
                                                        </div>
                                                        <div>
                                                            <label className={label}>Per utterance</label>
                                                            <select className={input + " app-select cursor-pointer pr-8"} disabled={readOnly}
                                                                value={d.multi ? "multi" : "single"}
                                                                onChange={(e) => setDim(i, { multi: e.target.value === "multi" })}>
                                                                <option value="single">Exactly one code</option>
                                                                <option value="multi">Any number of codes</option>
                                                            </select>
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <label className={label}>Guidance (the rule for the whole dimension, optional)</label>
                                                        <textarea className={area} rows={2} disabled={readOnly} value={d.guidance}
                                                            onChange={(e) => setDim(i, { guidance: e.target.value })} />
                                                    </div>
                                                    <div className="overflow-hidden rounded-lg border border-tiilt-line">
                                                        <div className="grid grid-cols-[8rem_1fr_1fr_auto] gap-2 bg-tiilt-ground/60 px-3 py-1.5 font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                                                            <span>Code</span>
                                                            <span>Definition</span>
                                                            <span>Examples (one per line)</span>
                                                            <span />
                                                        </div>
                                                        {d.codes.map((c, k) => (
                                                            <div key={c.id} className="grid grid-cols-[8rem_1fr_1fr_auto] items-start gap-2 border-t border-tiilt-line px-3 py-2">
                                                                <div className="flex flex-col gap-1">
                                                                    <input className={input} maxLength={40} disabled={readOnly} value={c.label}
                                                                        placeholder="Label" onChange={(e) => setCode(i, k, { label: e.target.value })} />
                                                                    <input className={input + " font-ahamono text-xs"} maxLength={24} disabled={readOnly}
                                                                        value={c.code} placeholder={slugify(c.label) || "code"}
                                                                        onChange={(e) => setCode(i, k, { code: e.target.value })} />
                                                                </div>
                                                                <textarea className={area} rows={3} maxLength={400} disabled={readOnly} value={c.definition}
                                                                    onChange={(e) => setCode(i, k, { definition: e.target.value })} placeholder="When this code applies" />
                                                                <textarea className={area} rows={3} disabled={readOnly} value={c.examples}
                                                                    onChange={(e) => setCode(i, k, { examples: e.target.value })} placeholder="Example utterances" />
                                                                {!readOnly ? (
                                                                    <button className="cursor-pointer rounded px-1.5 py-1 text-xs text-tiilt-muted hover:text-tiilt-danger"
                                                                        title="Remove this code"
                                                                        onClick={() => setDim(i, { codes: d.codes.filter((_, m) => m !== k) })}>
                                                                        ✕
                                                                    </button>
                                                                ) : <span />}
                                                            </div>
                                                        ))}
                                                    </div>
                                                    <div className="flex flex-wrap items-end gap-3">
                                                        {!readOnly ? (
                                                            <button className={btnSecondarySm} onClick={() => setDim(i, { codes: [...d.codes, emptyCode()] })}>
                                                                + Add code
                                                            </button>
                                                        ) : null}
                                                        {!d.multi ? (
                                                            <div className="min-w-48">
                                                                <label className={label}>Default when nothing applies</label>
                                                                <select className={input + " app-select cursor-pointer pr-8"} disabled={readOnly}
                                                                    value={slugify(d.default) || ""} onChange={(e) => setDim(i, { default: e.target.value })}>
                                                                    <option value="">Automatic (a "none"/"neutral" code, else the last)</option>
                                                                    {d.codes.map((c) => {
                                                                        const code = slugify(c.code || c.label)
                                                                        return code ? <option key={c.id} value={code}>{c.label || code}</option> : null
                                                                    })}
                                                                </select>
                                                            </div>
                                                        ) : null}
                                                    </div>
                                                    <div>
                                                        <label className={label}>Conventions (tie-break rules, one per line, optional)</label>
                                                        <textarea className={area} rows={2} disabled={readOnly} value={d.conventions}
                                                            onChange={(e) => setDim(i, { conventions: e.target.value })} />
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                        {!readOnly ? (
                                            <button className={btnSecondary + " self-start"} onClick={() => set({ dimensions: [...form.dimensions, emptyDimension()] })}>
                                                + Add dimension
                                            </button>
                                        ) : null}
                                    </div>
                                </>
                            ) : null}
                            {error ? <div className={dlgError}>{error}</div> : null}
                            {saved && !error ? <div className="text-sm text-tiilt-teal-text">Saved.</div> : null}
                        </div>
                    </div>
                    <div className="flex w-full flex-none flex-wrap items-center justify-center gap-3 border-t border-tiilt-line bg-white px-4 py-3">
                        <button className={btnSecondary} onClick={() => navigate("/coding-schemes")}>
                            Back to schemes
                        </button>
                        {!readOnly ? (
                            <button className={btnPrimary + " inline-flex items-center gap-2"} onClick={save} disabled={busy}>
                                {busy ? <InlineSpinner /> : null}
                                {schemeId ? "Save changes" : "Save scheme"}
                            </button>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    )
}

export { CodingSchemeEditorComponent }
