import { useState } from "react"
import { useNavigate } from "react-router-dom"
import backicon from "../assets/img/icon-back.svg"

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
            className="mr-2 flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full text-sm transition hover:bg-tiilt-soft"
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
            className="flex h-8 w-8 flex-none cursor-pointer items-center justify-center rounded-full text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
        >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" stroke="currentColor" strokeWidth="1.8" />
                <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06c.5.5 1.25.63 1.87.34H9a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.09c0 .68.4 1.3 1.03 1.56.62.29 1.37.16 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V9c.26.63.88 1.03 1.56 1.03H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.56 1.03z" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        </button>
    )
}

function Appheader(props) {
    return (
        <div className="relative top-0 z-10 flex h-14 w-full flex-none flex-row items-center border-b border-tiilt-line bg-white">
            {props.leftText !== false ? (
                <div
                    onClick={props.nav}
                    className="w-min cursor-pointer p-4 text-sm font-semibold whitespace-nowrap text-tiilt-muted transition hover:text-tiilt"
                >
                    {props.leftText}
                </div>
            ) : (
                <p
                    className="flex w-max cursor-pointer items-center gap-1 p-4 text-sm font-semibold text-tiilt-muted transition hover:text-tiilt"
                    onClick={props.nav}
                >
                    <img alt="" className="h-4 w-4" src={backicon} />
                    Back
                </p>
            )}
            <div className="w-full overflow-hidden text-center text-base font-semibold whitespace-nowrap text-tiilt-ink select-none">
                {props.editMode ? (
                    <input
                        className="visible w-52 overflow-scroll border-0 text-center outline-none"
                        type="text"
                        defaultValue={props.title}
                        onKeyUp={(event) =>
                            props.changeInputVal(event.target.value)
                        }
                    />
                ) : (
                    props.title
                )}
            </div>
            <div
                onClick={props.rightTextClick}
                className="w-max cursor-pointer px-4 text-center text-sm font-semibold whitespace-nowrap text-tiilt transition hover:text-tiilt-deep"
            >
                {props.rightText}
            </div>
            <SettingsButton />
            <ThemeToggle />
        </div>
    )
}

export { Appheader, ThemeToggle }
