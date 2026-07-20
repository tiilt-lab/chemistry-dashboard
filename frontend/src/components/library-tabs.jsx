import { Link, useLocation } from "react-router-dom"

// The Library section: keyword lists and topic models are two tabs of one
// configuration area, not two unrelated top-level pages.
export function LibraryTabs() {
    const { pathname } = useLocation()
    const tabs = [
        { label: "Keyword lists", to: "/keyword-lists" },
        { label: "Topic models", to: "/topic-models" },
    ]
    return (
        <div
            role="tablist"
            aria-label="Library"
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
