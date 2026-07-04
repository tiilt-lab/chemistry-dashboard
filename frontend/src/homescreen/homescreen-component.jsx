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
        name: "Discussions & Pods",
        desc: "Record and review sessions; manage recording devices",
        links: [
            { label: "Discussions", path: "/sessions", primary: true },
            { label: "Pods", path: "/pods" },
        ],
    },
    {
        icon: wordlist,
        name: "Keywords & Topics",
        desc: "Keyword lists for detection and topic models for analysis",
        links: [
            { label: "Keyword lists", path: "/keyword-lists", primary: true },
            { label: "Topic models", path: "/topic-models" },
        ],
    },
    {
        icon: pod,
        name: "Students & Raters",
        desc: "Manage student profiles and dashboard raters",
        links: [{ label: "Manage people", path: "/people", primary: true }],
    },
]

function GroupCard({ icon, name, desc, links, navigate }) {
    return (
        <div className="flex flex-col gap-4 rounded-xl border border-tiilt-line bg-white p-5 transition hover:shadow-[0_10px_24px_-14px_rgba(42,23,74,0.4)] sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
                <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-tiilt-soft">
                    <img alt="" src={icon} className="h-5 w-5" />
                </span>
                <span>
                    <span className="block text-base font-semibold text-tiilt-ink">
                        {name}
                    </span>
                    <span className="block text-sm text-tiilt-muted">
                        {desc}
                    </span>
                </span>
            </div>
            <div className="flex flex-none flex-wrap gap-2">
                {links.map((link) => (
                    <button
                        key={link.path}
                        onClick={() => navigate(link.path)}
                        className={
                            "rounded-lg px-4 py-2 text-sm font-semibold transition active:translate-y-px " +
                            (link.primary
                                ? "bg-tiilt text-white hover:bg-tiilt-deep"
                                : "border border-tiilt-line bg-white text-tiilt-ink hover:border-tiilt hover:bg-tiilt-soft")
                        }
                    >
                        {link.label}
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

            <main className="mx-auto w-full max-w-3xl px-4 py-8 md:py-12">
                <h2 className="text-2xl font-semibold text-tiilt-ink">
                    Good {timeOfDay}!
                </h2>
                <p className="mt-1 mb-8 max-w-[60ch] text-sm text-tiilt-muted">
                    Welcome to the Building Literacy in N-person Collaborations
                    (BLINC) dashboard. Start gathering analytic data by
                    recording a new discussion.
                </p>

                <div className="flex flex-col gap-4">
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
