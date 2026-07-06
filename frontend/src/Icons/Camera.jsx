// Video-camera glyph (was byte-identical inline copies in sessions +
// pods-overview).
export default function Camera({ size = 20 }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="2.5" y="6" width="12" height="12" rx="2.5" fill="currentColor" />
            <path d="M16 10l5-3v10l-5-3z" fill="currentColor" />
        </svg>
    )
}
