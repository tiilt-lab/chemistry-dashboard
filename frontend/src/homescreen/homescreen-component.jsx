import { useNavigate } from "react-router-dom"
import { updateTime } from "../utilities/helper-functions"
import { AuthService } from "../services/auth-service"
import { TiiltLogo } from "../components/tiilt-logo"

import recordicon from "../assets/img/icon-record.svg"
import wordlist from "../assets/img/icon-wordlist.svg"
import pod from "../assets/img/icon-pod.svg"
import settings from "../assets/img/settings.svg"
import question from "../assets/img/question.svg"
import logouticon from "../assets/img/logout.svg"

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

function HomeScreen() {
    const timeOfDay = updateTime()
    const navigate = useNavigate()

    const navigateToHelp = () => {
        window.open(
            window.location.protocol +
                "//" +
                window.location.hostname +
                "/help/Default.htm",
        )
    }

    const logout = () => {
        const ret = new AuthService().logout()
        ret.then(
            () => navigate("/login"),
            () => navigate("/login"),
        )
    }

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
                    <button
                        onClick={() => navigate("/settings")}
                        className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                    >
                        <img alt="" src={settings} className="h-4 w-4" />
                        Settings
                    </button>
                    <button
                        onClick={navigateToHelp}
                        className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                    >
                        <img alt="" src={question} className="h-4 w-4" />
                        Help
                    </button>
                    <button
                        onClick={logout}
                        className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-tiilt-muted transition hover:bg-tiilt-soft hover:text-tiilt"
                    >
                        <img alt="" src={logouticon} className="h-4 w-4" />
                        Sign out
                    </button>
                </div>
            </header>

            <main className="mx-auto w-full max-w-3xl px-4 py-8">
                <h2 className="text-2xl font-semibold tracking-tight text-tiilt-ink">
                    Good {timeOfDay}!
                </h2>
                <p className="mt-1 mb-6 max-w-[60ch] text-sm text-tiilt-muted">
                    Welcome to the BLINC dashboard. Start gathering analytic
                    data by recording a new session.
                </p>

                <div className="flex flex-col gap-3">
                    {GROUPS.map((g) => (
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
