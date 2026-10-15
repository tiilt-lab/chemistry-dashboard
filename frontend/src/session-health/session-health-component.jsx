import { useNavigate } from "react-router-dom"
import { Appheader } from "../header/header-component"
import { SessionTabs } from "../components/session-tabs"
import { useRequireManager } from "../routes/roles"
import { useHealth, HealthPanel } from "../ops/health-panel"

// Server load, inside the session workspace: during class the question is
// "is the server keeping up?", and the answer should be one tab away from
// the pods, not under Admin. Same panel and endpoint as Admin > Server
// health; managers only, like that page.
function SessionHealthComponent(props) {
    const navigate = useNavigate()
    const canView = useRequireManager(props.userdata)
    const { health, error } = useHealth(canView)
    return (
        <div role="main" className="main-container">
            <Appheader title={"Server load"} leftText={false} rightText={false} nav={() => navigate("/sessions")} escToBack={true} />
            <SessionTabs />
            <div className="toolbar-view-container">
                <div className="min-h-0 grow overflow-y-auto">
                    <div className="mx-auto w-full max-w-6xl px-4 py-8 lg:px-8">
                        <div className="mb-4">
                            <h2 className="text-lg font-semibold text-tiilt-ink">Server load</h2>
                            <p className="text-sm text-tiilt-muted">
                                CPU, GPU, memory, disk, live pods, the post-hoc queue and the services, for the whole server while this class runs.
                            </p>
                        </div>
                        <HealthPanel health={health} error={error} />
                    </div>
                </div>
            </div>
        </div>
    )
}

export { SessionHealthComponent }
