// Circular-arrow re-analyze glyph (was byte-identical inline copies in
// sessions + posthoc-trigger).
export default function Refresh({ size = 12 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
                d="M4 12a8 8 0 1 1 2.3 5.6M4 12H2m2 0V9"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
            />
        </svg>
    )
}
