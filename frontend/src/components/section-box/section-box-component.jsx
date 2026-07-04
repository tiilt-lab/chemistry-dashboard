import React, { useState } from "react"

function AppSectionBoxComponent(props) {
    const [isExpanded, setIsExpanded] = useState(true)

    const toggleExpand = () => setIsExpanded(!isExpanded)

    return (
        <div
            className={`relative flex h-min flex-col overflow-hidden rounded-xl border border-tiilt-line bg-white ${props.type || ""}`}
            style={
                props.maxHeight !== undefined
                    ? { maxHeight: props.maxHeight + "px" }
                    : {}
            }
        >
            <button
                type="button"
                onClick={toggleExpand}
                aria-expanded={isExpanded}
                className="flex w-full items-center justify-between gap-2 border-b border-tiilt-line bg-tiilt-ground/60 px-4 py-2.5 text-left transition hover:bg-tiilt-soft"
            >
                <span className="text-sm font-semibold text-tiilt-ink">
                    {props.heading}
                </span>
                <span
                    aria-hidden="true"
                    className={
                        "flex-none text-tiilt-muted transition-transform " +
                        (isExpanded ? "rotate-90" : "")
                    }
                >
                    ›
                </span>
            </button>
            {isExpanded ? <div className="p-3">{props.children}</div> : <></>}
        </div>
    )
}

export { AppSectionBoxComponent }
