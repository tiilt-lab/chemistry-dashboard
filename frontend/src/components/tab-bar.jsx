import { Link, useLocation } from "react-router-dom"

// Shared tab strip for the section navigators (Library / Session / Admin),
// which used to be three byte-identical components differing only in their
// tabs array and aria-label.
export function TabBar({ tabs, label }) {
    const { pathname } = useLocation()
    return (
        <div
            role="tablist"
            aria-label={label}
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
