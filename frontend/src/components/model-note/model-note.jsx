// One-line provenance note shown in every analysis section: which model
// computed the numbers above/below it. `label` comes from /api/v1/models so it
// always reflects the active configuration.
function ModelNote({ prefix = "Computed with", label, fallback }) {
    const text = label || fallback
    if (!text) return null
    return (
        <div className="text-xs text-tiilt-muted">
            {prefix} {text}
        </div>
    )
}

export { ModelNote }
