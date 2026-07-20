import { Link, useLocation, useParams } from "react-router-dom"

// Peer tabs of the session workspace. The Discussion Graph used to be
// reachable only through a toolbar menu item on the overview — a top-level
// route hidden behind a buried entry point.
export function SessionTabs() {
    const { sessionId } = useParams()
    const { pathname } = useLocation()
    const tabs = [
        { label: "Overview", to: `/sessions/${sessionId}/overview` },
        { label: "Discussion graph", to: `/sessions/${sessionId}/graph` },
    ]
    return (
        <div
            role="tablist"
            aria-label="Session views"
            className="flex h-10 w-full flex-none items-center gap-1 border-b border-tiilt-line bg-white px-3"
        >
            {tabs.map((t) => {
                const active =
                    pathname === t.to || pathname.startsWith(t.to + "/")
                return (
                    <Link
                        key={t.to}
                        to={t.to}
                        role="tab"
                        aria-selected={active}
                        className={
                            "rounded-md px-3 py-1.5 text-sm font-semibold transition " +
                            (active
                                ? "bg-tiilt-soft text-tiilt"
                                : "text-tiilt-muted hover:bg-tiilt-soft/60 hover:text-tiilt")
                        }
                    >
                        {t.label}
                    </Link>
                )
            })}
        </div>
    )
}
