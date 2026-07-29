import React, { useState } from "react"

// Evidence-tier badges: mark a section's metrics as replicated findings
// ("evidence-backed") or framework-derived signals ("exploratory") so the two
// don't read as equally authoritative.
const BADGE_STYLES = {
    teal: "bg-tiilt-teal/15 text-tiilt-teal",
    amber: "bg-tiilt-orange/15 text-tiilt-orange-text",
}

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
                <span className="flex items-center gap-2 text-sm font-semibold text-tiilt-ink">
                    {props.heading}
                    {props.badge && (
                        <span
                            className={
                                "rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide " +
                                (BADGE_STYLES[props.badgeTone] ||
                                    BADGE_STYLES.teal)
                            }
                        >
                            {props.badge}
                        </span>
                    )}
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
