// Shared empty-state block (was defined locally in create-session and
// hand-copied — sometimes with drifted sizing — on four other pages).
function EmptyState({ title, subtitle }) {
    return (
        <div className="flex flex-col items-center gap-1.5 py-10 text-center">
            <div className="text-lg font-semibold text-tiilt-ink">{title}</div>
            <div className="max-w-xs text-sm text-tiilt-muted">{subtitle}</div>
        </div>
    )
}

export { EmptyState }
