import { Appheader } from "../header/header-component"
import { useRequireManager } from "../routes/roles"
import { AdminTabs } from "../components/admin-tabs"
import { useHealth, HealthPanel } from "./health-panel"

// Admin > Server health: the shared health panel under the admin tabs. The
// same panel is the session page's Server load tab.
export function OpsComponent(props) {
    // Server internals are admin territory; this page used to be reachable by
    // any signed-in account that knew the URL.
    const canView = useRequireManager(props.userdata)
    const { health, error } = useHealth(canView)

    return (
        <div role="main" className="main-container">
            <Appheader title="Admin" leftText={false} rightText={""} />
            <AdminTabs />
            <div className="mx-auto w-full max-w-3xl overflow-y-auto px-4 py-6">
                <HealthPanel health={health} error={error} />
            </div>
        </div>
    )
}
