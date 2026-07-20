import { useEffect, useState } from "react"
import { Link, Outlet, useLocation } from "react-router-dom"
import { AuthService } from "../services/auth-service"
import { isManager } from "../routes/roles"
import { TiiltLogo } from "../components/tiilt-logo"

// Persistent left rail: the app's global navigation. Mounted once as a layout
// route around every signed-in page, so moving between sections no longer
// means going back to /home. Collapses to an icon rail below lg.
//
// "Devices" is the physical recorder hardware (/devices; /pods redirects);
// a group inside a session stays a "Group". "Library" fronts the
// keyword/topic configuration cluster.

function IconSessions(props) {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <circle cx="12" cy="12" r="9" />
            <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none" />
        </svg>
    )
}
function IconStudents(props) {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <circle cx="9" cy="8" r="3.5" />
            <path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" />
            <path d="M16 5.5a3.5 3.5 0 0 1 0 5" />
            <path d="M18.5 14.5c1.9.9 3 2.6 3 5.5" />
        </svg>
    )
}
function IconDevices(props) {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <rect x="5" y="3" width="14" height="18" rx="3" />
            <circle cx="12" cy="14" r="3.5" />
            <line x1="9" y1="7" x2="15" y2="7" />
        </svg>
    )
}
function IconLibrary(props) {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        </svg>
    )
}
function IconAdmin(props) {
    return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <path d="M12 2l8 4v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6l8-4z" />
            <path d="M9.5 12l2 2 3.5-4" />
        </svg>
    )
}

const NAV_ITEMS = [
    { label: "Sessions", to: "/sessions", match: ["/sessions"], Icon: IconSessions },
    { label: "Students", to: "/students", match: ["/students"], Icon: IconStudents },
    { label: "Devices", to: "/devices", match: ["/devices", "/pods"], Icon: IconDevices },
    {
        label: "Library",
        to: "/keyword-lists",
        match: ["/keyword-lists", "/topic-models", "/topic-list", "/file_upload"],
        Icon: IconLibrary,
    },
]

const ADMIN_ITEM = {
    label: "Admin",
    to: "/users",
    match: ["/users", "/raters", "/ops"],
    Icon: IconAdmin,
}

function NavItem({ item, active }) {
    const { Icon } = item
    return (
        <Link
            to={item.to}
            title={item.label}
            aria-current={active ? "page" : undefined}
            className={
                "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-semibold transition " +
                (active
                    ? "bg-tiilt-soft text-tiilt"
                    : "text-tiilt-muted hover:bg-tiilt-soft/60 hover:text-tiilt")
            }
        >
            <Icon className="flex-none" />
            <span className="hidden truncate lg:inline">{item.label}</span>
        </Link>
    )
}

function AppSidebar({ me }) {
    const location = useLocation()
    const items = isManager(me) ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS
    const activeOf = (item) =>
        item.match.some(
            (p) => location.pathname === p || location.pathname.startsWith(p + "/"),
        )
    return (
        <aside
            aria-label="Primary"
            className="flex h-full w-14 flex-none flex-col border-r border-tiilt-line bg-white lg:w-44"
        >
            <Link
                to="/home"
                title="Home"
                className="flex h-14 flex-none items-center gap-2 border-b border-tiilt-line px-3.5 text-tiilt"
            >
                <TiiltLogo className="h-7 w-7 flex-none" />
                <span className="hidden text-base leading-none font-extrabold text-tiilt-ink lg:inline">
                    BLINC
                </span>
            </Link>
            <nav className="flex flex-col gap-1 p-2">
                {items.map((item) => (
                    <NavItem
                        key={item.label}
                        item={item}
                        active={activeOf(item)}
                    />
                ))}
            </nav>
        </aside>
    )
}

function AppShell() {
    const [me, setMe] = useState(null)
    useEffect(() => {
        new AuthService().me((u) => {
            if (u && u !== "cors error") setMe(u)
        })
    }, [])
    return (
        <>
            <AppSidebar me={me} />
            <div className="flex h-full min-w-0 grow flex-col">
                <Outlet />
            </div>
        </>
    )
}

export { AppShell }
