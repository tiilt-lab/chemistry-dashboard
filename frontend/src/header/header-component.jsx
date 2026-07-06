import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import backicon from "../assets/img/icon-back.svg"

// Opt-in (escToBack prop): Escape triggers the header Back action, so the
// keyboard can walk back up the session hierarchy. Deliberately inert while
// a dialog or context menu is open (their own Escape handling wins) and
// while the user is typing in a field.
function useEscapeBack(enabled, nav) {
    useEffect(() => {
        if (!enabled || !nav) return
        const onKey = (e) => {
            if (e.key !== "Escape") return
            if (document.querySelector('[role="dialog"], [role="menu"]'))
                return
            const t = e.target
            if (
                t &&
                (t.tagName === "INPUT" ||
                    t.tagName === "TEXTAREA" ||
                    t.tagName === "SELECT" ||
                    t.isContentEditable)
            )
                return
            nav()
        }
        document.addEventListener("keydown", onKey)
        return () => document.removeEventListener("keydown", onKey)
    }, [enabled, nav])
}

function ThemeToggle() {
    const [dark, setDark] = useState(
        document.documentElement.classList.contains("dark"),
    )
    const flip = () => {
        const next = !dark
        document.documentElement.classList.toggle("dark", next)
        localStorage.setItem("theme", next ? "dark" : "light")
        setDark(next)
    }
    return (
        <button
            onClick={flip}
            title={dark ? "Switch to light mode" : "Switch to dark mode"}
            className="flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full text-sm transition hover:bg-tiilt-soft"
        >
            {dark ? "\u2600\ufe0f" : "\ud83c\udf19"}
        </button>
    )
}

function SettingsButton() {
    const navigate = useNavigate()
    return (
        <button
            onClick={() => navigate("/settings")}
            title="Settings"
            className="mr-3 ml-2 flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
        >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" stroke="currentColor" strokeWidth="1.8" />
                <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06c.5.5 1.25.63 1.87.34H9a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.09c0 .68.4 1.3 1.03 1.56.62.29 1.37.16 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V9c.26.63.88 1.03 1.56 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        </button>
    )
}

function Appheader(props) {
    useEscapeBack(props.escToBack, props.nav)
    return (
        <div className="relative top-0 z-10 flex h-14 w-full flex-none flex-row items-center border-b border-tiilt-line bg-white">
            {props.leftText !== false ? (
                <button
                    onClick={props.nav}
                    className="w-min cursor-pointer p-4 text-sm font-semibold whitespace-nowrap text-tiilt-muted transition hover:text-tiilt"
                >
                    {props.leftText}
                </button>
            ) : (
                <button
                    className="flex w-max cursor-pointer items-center gap-1 p-4 text-sm font-semibold text-tiilt-muted transition hover:text-tiilt"
                    onClick={props.nav}
                >
                    <img alt="" className="h-4 w-4" src={backicon} />
                    Back
                </button>
            )}
            <div className="min-w-0 flex-1 truncate px-2 text-center text-sm font-semibold text-tiilt-ink select-none sm:text-base">
                {props.editMode ? (
                    <input
                        className="visible w-52 overflow-scroll border-0 text-center outline-none"
                        type="text"
                        aria-label="Title"
                        defaultValue={props.title}
                        onKeyUp={(event) =>
                            props.changeInputVal(event.target.value)
                        }
                    />
                ) : (
                    <h1 className="truncate text-sm font-semibold sm:text-base">
                        {props.title}
                    </h1>
                )}
            </div>
            {props.rightPill ? (
                <span className="mr-1 flex-none rounded-full bg-tiilt-line/40 px-2.5 py-1 text-xs font-semibold tracking-wide text-tiilt-muted uppercase">
                    {props.rightPill}
                </span>
            ) : null}
            {props.rightText ? (
                <button
                    onClick={props.rightTextClick}
                    className="w-max cursor-pointer px-4 text-center text-sm font-semibold whitespace-nowrap text-tiilt transition hover:text-tiilt-deep"
                >
                    {props.rightText}
                </button>
            ) : null}
            <ThemeToggle />
            <SettingsButton />
        </div>
    )
}

export { Appheader, ThemeToggle }
