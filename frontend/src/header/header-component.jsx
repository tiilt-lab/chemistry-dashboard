import { useState } from "react"
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
            <ThemeToggle />
        </div>
    )
}

export { Appheader, ThemeToggle }
