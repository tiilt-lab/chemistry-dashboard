// One pill for every status chip (Analyzed / Analyzing / Live / Queued /
// No data / Error / counts). Fixes the px-1.5-vs-px-2 drift between pages
// and centralizes tone colors.
const TONES = {
    teal: "bg-tiilt-teal/15 text-tiilt-teal-text",
    orange: "bg-tiilt-orange/15 text-tiilt-orange-text",
    brand: "bg-tiilt-soft text-tiilt",
    neutral: "bg-tiilt-line/40 text-tiilt-muted",
    danger: "bg-tiilt-danger-soft text-tiilt-danger",
}

const DOT = {
    teal: "bg-tiilt-teal",
    orange: "bg-tiilt-orange",
    brand: "bg-tiilt",
    neutral: "bg-tiilt-muted",
    danger: "bg-tiilt-danger",
}

function StatusPill({ tone = "neutral", pulse = false, dot = false, title, className = "", children }) {
    return (
        <span
            title={title}
            className={
                "flex flex-none items-center gap-1 rounded-full px-2 py-0.5 font-semibold whitespace-nowrap " +
                (TONES[tone] || TONES.neutral) +
                (className ? " " + className : "")
            }
        >
            {pulse || dot ? (
                <span
                    className={
                        "h-1.5 w-1.5 rounded-full " +
                        (DOT[tone] || DOT.neutral) +
                        (pulse ? " animate-pulse" : "")
                    }
                />
            ) : null}
            {children}
        </span>
    )
}

export { StatusPill }
