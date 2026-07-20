import { Link, useLocation } from "react-router-dom"

// The Admin area: account management, rater assignments, and server health
// present as one guarded section instead of three unrelated pages (one of
// which — /ops — used to be reachable only by typing the URL).
export function AdminTabs() {
    const { pathname } = useLocation()
    const tabs = [
        { label: "Users", to: "/users" },
        { label: "Raters", to: "/raters" },
        { label: "Server health", to: "/ops" },
    ]
    return (
        <div
            role="tablist"
            aria-label="Administration"
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
