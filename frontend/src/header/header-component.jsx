import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import Chevron from "../Icons/Chevron"
import GearIcon from "../Icons/Settings"

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
            <GearIcon />
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
                    <Chevron direction="left" size={16} />
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
                props.rightPillClick ? (
                    <button
                        onClick={props.rightPillClick}
                        className="mr-1 flex-none cursor-pointer rounded-full bg-tiilt-line/40 px-2.5 py-1 text-xs font-semibold tracking-wide text-tiilt-muted uppercase transition hover:bg-tiilt-line/70 hover:text-tiilt-ink"
                    >
                        {props.rightPill}
                    </button>
                ) : (
                    <span className="mr-1 flex-none rounded-full bg-tiilt-line/40 px-2.5 py-1 text-xs font-semibold tracking-wide text-tiilt-muted uppercase">
                        {props.rightPill}
                    </span>
                )
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
