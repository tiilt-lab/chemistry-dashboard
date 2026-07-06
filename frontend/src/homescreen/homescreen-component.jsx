import { useNavigate } from "react-router-dom"
import { ThemeToggle } from "../header/header-component"
import GearIcon from "../Icons/Settings"
import { updateTime } from "../utilities/helper-functions"
import { TiiltLogo } from "../components/tiilt-logo"

import recordicon from "../assets/img/icon-record.svg"
import wordlist from "../assets/img/icon-wordlist.svg"
import pod from "../assets/img/icon-pod.svg"

const GROUPS = [
    {
        icon: recordicon,
        name: "Sessions & Pods",
        links: [
            {
                label: "Sessions",
                desc: "Record new sessions and review past ones",
                path: "/sessions",
            },
            {
                label: "Pods",
                desc: "Recording devices and their connection status",
                path: "/pods",
            },
        ],
    },
    {
        icon: wordlist,
        name: "Keywords & Topics",
        links: [
            {
                label: "Keyword lists",
                desc: "Terms to detect as they come up in session",
                path: "/keyword-lists",
            },
            {
                label: "Topic models",
                desc: "Models that tag what each utterance is about",
                path: "/topic-models",
            },
        ],
    },
    {
        icon: pod,
        name: "Students & Raters",
        links: [
            {
                label: "Manage people",
                desc: "Student profiles and dashboard raters",
                path: "/people",
            },
        ],
    },
]

// Admin/super-only card, appended to GROUPS when the signed-in user can manage
// accounts. Kept separate so the base groups stay visible to everyone.
const ADMIN_GROUP = {
    icon: pod,
    name: "Administration",
    links: [
        {
            label: "Users",
            desc: "Dashboard accounts, roles, and access",
            path: "/users",
        },
    ],
}

function GroupCard({ icon, name, links, navigate }) {
    return (
        <div className="overflow-hidden rounded-xl border border-tiilt-line bg-white shadow-[0_1px_2px_rgba(42,23,74,0.05)]">
            <div className="flex items-center gap-2.5 border-b border-tiilt-line bg-tiilt-ground/60 px-5 py-2">
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-md bg-tiilt-soft">
                    <img alt="" src={icon} className="h-3.5 w-3.5" />
                </span>
                <span className="font-ahamono text-[11px] tracking-wider text-tiilt-muted uppercase">
                    {name}
                </span>
            </div>
            <div className="divide-y divide-tiilt-line">
                {links.map((link) => (
                    <button
                        key={link.path}
                        onClick={() => navigate(link.path)}
                        className="group flex w-full items-center gap-3 px-5 py-2.5 text-left transition hover:bg-tiilt-soft"
                    >
                        <span className="flex-none text-[15px] font-semibold text-tiilt-ink group-hover:text-tiilt">
                            {link.label}
                        </span>
                        <span className="hidden grow truncate text-sm text-tiilt-muted sm:block">
                            {link.desc}
                        </span>
                        <span
                            aria-hidden="true"
                            className="flex-none text-tiilt-muted transition group-hover:translate-x-0.5 group-hover:text-tiilt"
                        >
                            ›
                        </span>
                    </button>
                ))}
            </div>
        </div>
    )
}

function HomeScreen(props) {
    const timeOfDay = updateTime()
    const navigate = useNavigate()
    const user = props.userdata
    const canManageUsers = user && (user.isAdmin || user.isSuper)
    const groups = canManageUsers ? [...GROUPS, ADMIN_GROUP] : GROUPS

    return (
        <div className="main-container overflow-y-auto bg-tiilt-ground">
            <header className="flex h-14 w-full flex-none items-center gap-3 border-b border-tiilt-line bg-white px-4 md:px-8">
                <TiiltLogo className="h-8 w-8 text-tiilt" />
                <div className="text-lg leading-none font-extrabold text-tiilt-ink">
                    BLINC{" "}
                    <span className="font-ahamono text-sm font-normal text-tiilt-muted">
                        (by&nbsp;
                        <a
                            href="https://tiilt.northwestern.edu"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-semibold text-tiilt hover:underline"
                        >
                            tiilt
                        </a>
                        )
                    </span>
                </div>
                <div className="ml-auto flex items-center gap-2">
                    <ThemeToggle />
                    <button
                        onClick={() => navigate("/settings")}
                        title="Settings"
                        className="flex flex-none items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold whitespace-nowrap text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                    >
                        <GearIcon />
                        <span className="hidden sm:inline">Settings</span>
                    </button>
                </div>
            </header>

            <main className="mx-auto w-full max-w-3xl px-4 py-8">
                <h1 className="text-2xl font-semibold tracking-tight text-tiilt-ink">
                    Good {timeOfDay}!
                </h1>
                <p className="mt-1 mb-6 max-w-[60ch] text-sm text-tiilt-muted">
                    Welcome to the BLINC dashboard. Start gathering analytic
                    data by recording a new session.
                </p>

                <div className="flex flex-col gap-3">
                    {groups.map((g) => (
                        <GroupCard
                            key={g.name}
                            icon={g.icon}
                            name={g.name}
                            desc={g.desc}
                            links={g.links}
                            navigate={navigate}
                        />
                    ))}
                </div>
            </main>
        </div>
    )
}

export { HomeScreen }
