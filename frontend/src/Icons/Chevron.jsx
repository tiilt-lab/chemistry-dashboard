// One chevron for the whole app (rows, expanders, breadcrumb affordances).
const PATHS = {
    right: "M9 6l6 6-6 6",
    left: "M15 6l-6 6 6 6",
    down: "M6 9l6 6 6-6",
    up: "M18 15l-6-6-6 6",
}

export default function Chevron({ direction = "right", size = 14, className, style }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
            className={className}
            style={style}
        >
            <path
                d={PATHS[direction] || PATHS.right}
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    )
}
