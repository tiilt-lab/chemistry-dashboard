import { useNavigate } from "react-router-dom"
import { updateTime } from "../utilities/helper-functions"
import { AuthService } from "../services/auth-service"
import { TiiltLogo } from "../components/tiilt-logo"

import recordicon from "../assets/img/icon-record.svg"
import wordlist from "../assets/img/icon-wordlist.svg"
import pod from "../assets/img/icon-pod.svg"
import trending from "../assets/img/icon-trending-up.svg"
import settings from "../assets/img/settings.svg"
import question from "../assets/img/question.svg"
import logouticon from "../assets/img/logout.svg"

const MENUS = [
    {
        icon: recordicon,
        name: "Discussions",
        desc: "Record and review discussion sessions",
        path: "/sessions",
    },
    {
        icon: wordlist,
        name: "Keywords",
        desc: "Manage keyword lists for detection",
        path: "/keyword-lists",
    },
    {
        icon: pod,
        name: "Pods",
        desc: "Recording devices and their status",
        path: "/pods",
    },
    {
        icon: trending,
        name: "Topic modeling",
        desc: "Train and manage topic models",
        path: "/topic-models",
    },
]

function MenuCard({ icon, name, desc, onClick }) {
    return (
        <button
            onClick={onClick}
            className="flex items-center gap-4 rounded-xl border border-tiilt-line bg-white p-4 text-left transition hover:border-tiilt hover:shadow-[0_10px_24px_-14px_rgba(42,23,74,0.4)] active:translate-y-px"
        >
            <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-tiilt-soft">
                <img alt="" src={icon} className="h-5 w-5" />
            </span>
            <span>
                <span className="block text-base font-semibold text-tiilt-ink">
                    {name}
                </span>
                <span className="block text-sm text-tiilt-muted">{desc}</span>
            </span>
        </button>
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
                    <span className="font-ahamono text-xs font-normal text-tiilt-muted">
                        (by&nbsp;
                        <span className="text-tiilt-orange">tiilt</span>)
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

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {MENUS.map((m) => (
                        <MenuCard
                            key={m.path}
                            icon={m.icon}
                            name={m.name}
                            desc={m.desc}
                            onClick={() => navigate(m.path)}
                        />
                    ))}
                </div>
            </main>
        </div>
    )
}

export { HomeScreen }
