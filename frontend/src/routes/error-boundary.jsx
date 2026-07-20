import React from "react"

// A deploy replaces the hashed chunk files on disk. A tab opened before the
// deploy still references the old names, so its next lazy route-load 404s,
// the import rejects, and — with no boundary — React unmounted the whole
// tree: blank screen, dead back button, manual reload the only way out.
const isChunkError = (err) =>
    /failed to fetch dynamically imported module|error loading dynamically imported module|importing a module script failed/i.test(
        String((err && err.message) || err),
    )

// One reload per minute max, so a genuinely broken server can't reload-loop.
export const reloadOnceForNewDeploy = () => {
    const last = Number(sessionStorage.getItem("chunkReloadAt") || 0)
    if (Date.now() - last < 60_000) return false
    sessionStorage.setItem("chunkReloadAt", String(Date.now()))
    window.location.reload()
    return true
}

export class RouteErrorBoundary extends React.Component {
    state = { error: null }

    static getDerivedStateFromError(error) {
        return { error }
    }

    componentDidCatch(error) {
        // Stale-deploy chunk 404: recover silently with a one-shot reload.
        if (isChunkError(error)) reloadOnceForNewDeploy()
    }

    render() {
        if (!this.state.error) return this.props.children
        return (
            <div className="flex h-full w-full grow items-center justify-center bg-tiilt-ground p-6">
                <div className="flex max-w-sm flex-col items-center gap-3 rounded-xl border border-tiilt-line bg-white p-6 text-center">
                    <div className="text-base font-semibold text-tiilt-ink">
                        Something went wrong
                    </div>
                    <div className="text-sm text-tiilt-muted">
                        {isChunkError(this.state.error)
                            ? "The dashboard was updated since this tab was opened."
                            : "This page hit an unexpected error."}{" "}
                        Reloading usually fixes it.
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="cursor-pointer rounded-lg bg-tiilt px-4 py-2 text-sm font-semibold text-white transition hover:bg-tiilt-deep"
                    >
                        Reload
                    </button>
                </div>
            </div>
        )
    }
}
