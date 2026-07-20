import { useState, useRef, useEffect } from "react"

// Clickable speaker label on a transcript line: "this section is from…".
// Click it, pick the right participant, and either fix just this line or
// every line currently sharing this label (a diarization cluster is usually
// all-or-nothing wrong, so the bulk action is the common case).
export function SpeakerReassign({ tag, roster, count, onReassign, disabled }) {
    const [open, setOpen] = useState(false)
    const [busy, setBusy] = useState(false)
    const ref = useRef(null)

    useEffect(() => {
        if (!open) return
        const away = (e) => {
            if (ref.current && !ref.current.contains(e.target)) setOpen(false)
        }
        document.addEventListener("mousedown", away)
        document.addEventListener("keydown", (e) => e.key === "Escape" && setOpen(false))
        return () => document.removeEventListener("mousedown", away)
    }, [open])

    const pick = async (alias, applyToTag) => {
        setBusy(true)
        try {
            await onReassign(alias, applyToTag)
            setOpen(false)
        } finally {
            setBusy(false)
        }
    }

    const label = tag || "Unlabeled"
    return (
        <span className="relative inline-block" ref={ref}>
            <button
                type="button"
                disabled={disabled}
                onClick={() => setOpen((v) => !v)}
                title={disabled ? label : "Reassign speaker"}
                className={
                    "rounded px-1 font-semibold text-tiilt transition " +
                    (disabled
                        ? "cursor-default"
                        : "cursor-pointer hover:bg-tiilt-soft hover:underline decoration-dotted")
                }
            >
                {label}:
            </button>
            {open ? (
                <div
                    role="menu"
                    className="absolute top-full left-0 z-20 mt-1 w-60 rounded-lg border border-tiilt-line bg-white p-1 shadow-pop"
                >
                    <div className="px-2 py-1 text-[11px] font-semibold tracking-wide text-tiilt-muted uppercase">
                        This section is from…
                    </div>
                    {roster.length === 0 ? (
                        <div className="px-2 py-2 text-xs text-tiilt-muted">
                            No participants on file for this group.
                        </div>
                    ) : (
                        roster.map((alias) => (
                            <div
                                key={alias}
                                className="flex items-center gap-1 rounded-md px-1 py-0.5 hover:bg-tiilt-soft/50"
                            >
                                <button
                                    type="button"
                                    disabled={busy}
                                    onClick={() => pick(alias, false)}
                                    className="flex-1 truncate rounded px-2 py-1 text-left text-sm text-tiilt-ink"
                                    title="Reassign only this line"
                                >
                                    {alias}
                                    {alias === tag ? (
                                        <span className="ml-1 text-tiilt-muted">
                                            (current)
                                        </span>
                                    ) : null}
                                </button>
                                {count > 1 && tag ? (
                                    <button
                                        type="button"
                                        disabled={busy}
                                        onClick={() => pick(alias, true)}
                                        title={`Apply to all ${count} segments currently labeled "${tag}"`}
                                        className="flex-none rounded px-1.5 py-1 text-[11px] font-semibold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                                    >
                                        all {count}
                                    </button>
                                ) : null}
                            </div>
                        ))
                    )}
                </div>
            ) : null}
        </span>
    )
}
