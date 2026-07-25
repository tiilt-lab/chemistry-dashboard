import { useState, useRef, useEffect, useCallback } from "react"
import { createPortal } from "react-dom"

const MENU_W = 240 // matches the menu's rendered width
const MENU_MAX_H = 280

// Clickable speaker label on a transcript line: "this section is from…".
// Click it, pick the right participant, and either fix just this line or
// every line currently sharing this label (a diarization cluster is usually
// all-or-nothing wrong, so the bulk action is the common case).
//
// The menu renders in a portal on document.body, positioned from the button's
// viewport rect. It used to be absolutely positioned inside the row, where the
// transcript list's own scroll container (overflow-y-auto) clipped it — z-index
// cannot escape an ancestor's overflow, so most of the menu was cut off.
export function SpeakerReassign({ tag, roster, count, onReassign, disabled, color }) {
    const [open, setOpen] = useState(false)
    const [busy, setBusy] = useState(false)
    const [guestMode, setGuestMode] = useState(false)
    const [guestName, setGuestName] = useState("")
    const [pos, setPos] = useState(null)
    const ref = useRef(null)
    const menuRef = useRef(null)

    // Anchor under the button, flipping above it when the viewport has no room
    // below, and keeping the menu inside the left/right edges.
    const place = useCallback(() => {
        const el = ref.current
        if (!el) return
        const r = el.getBoundingClientRect()
        const below = window.innerHeight - r.bottom
        const flip = below < MENU_MAX_H && r.top > below
        setPos({
            top: flip ? undefined : r.bottom + 4,
            bottom: flip ? window.innerHeight - r.top + 4 : undefined,
            left: Math.max(8, Math.min(r.left, window.innerWidth - MENU_W - 8)),
        })
    }, [])

    useEffect(() => {
        if (!open) return
        place()
        // The menu is no longer a DOM descendant of the button, so an
        // outside-click test has to check both.
        const away = (e) => {
            if (
                ref.current && !ref.current.contains(e.target) &&
                menuRef.current && !menuRef.current.contains(e.target)
            ) {
                setOpen(false)
            }
        }
        const onKey = (e) => e.key === "Escape" && setOpen(false)
        // Follow the anchor while the transcript list or page scrolls
        // (capture: the scroll happens on an inner container, not window).
        document.addEventListener("mousedown", away)
        document.addEventListener("keydown", onKey)
        window.addEventListener("scroll", place, true)
        window.addEventListener("resize", place)
        return () => {
            document.removeEventListener("mousedown", away)
            // The old cleanup dropped only the mousedown listener, leaking one
            // Escape handler per open.
            document.removeEventListener("keydown", onKey)
            window.removeEventListener("scroll", place, true)
            window.removeEventListener("resize", place)
        }
    }, [open, place])

    const pick = async (alias, applyToTag, guest = false) => {
        setBusy(true)
        try {
            await onReassign(alias, applyToTag, guest)
            setOpen(false)
            setGuestMode(false)
            setGuestName("")
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
                style={color ? { color } : undefined}
                title={disabled ? label : "Reassign speaker"}
                className={
                    "rounded px-1 font-semibold transition " +
                    (tag ? "text-tiilt " : "text-tiilt-muted ") +
                    (disabled
                        ? "cursor-default"
                        : "cursor-pointer underline decoration-dotted underline-offset-2 hover:bg-tiilt-soft")
                }
            >
                {label}:
            </button>
            {open && pos ? createPortal(
                <div
                    role="menu"
                    ref={menuRef}
                    style={{
                        position: "fixed",
                        top: pos.top,
                        bottom: pos.bottom,
                        left: pos.left,
                        width: MENU_W,
                        maxHeight: MENU_MAX_H,
                    }}
                    className="z-50 overflow-y-auto rounded-lg border border-tiilt-line bg-white p-1 shadow-pop"
                >
                    <div className="px-2 py-1 text-[11px] font-semibold tracking-wide text-tiilt-muted uppercase">
                        This section is from…
                    </div>
                    {roster.length === 0 && !guestMode ? (
                        <div className="px-2 py-2 text-xs text-tiilt-muted">
                            No participants on file for this group.
                        </div>
                    ) : (
                        !guestMode &&
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
                    {guestMode ? (
                        <form
                            className="flex items-center gap-1 px-1 py-1"
                            onSubmit={(e) => {
                                e.preventDefault()
                                const name = guestName.trim()
                                if (name) pick(name, false, true)
                            }}
                        >
                            <input
                                autoFocus
                                value={guestName}
                                onChange={(e) => setGuestName(e.target.value)}
                                placeholder="Guest's name"
                                maxLength={64}
                                className="w-full rounded border border-tiilt-line px-2 py-1 text-sm text-tiilt-ink outline-none focus:border-tiilt"
                            />
                            <button
                                type="submit"
                                disabled={busy || !guestName.trim()}
                                className="flex-none rounded bg-tiilt px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
                            >
                                Add
                            </button>
                        </form>
                    ) : (
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => setGuestMode(true)}
                            className="mt-0.5 w-full rounded-md border-t border-tiilt-line px-2 py-1.5 text-left text-xs font-semibold text-tiilt-muted transition hover:bg-tiilt-soft/50 hover:text-tiilt"
                            title="Attribute to someone who isn't in this group's roster — they'll be added as a speaker on this group"
                        >
                            Someone else…
                        </button>
                    )}
                </div>,
                document.body,
            ) : null}
        </span>
    )
}
