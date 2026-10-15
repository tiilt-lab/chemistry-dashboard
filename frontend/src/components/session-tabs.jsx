import { useParams } from "react-router-dom"
import { TabBar } from "./tab-bar"
import { getAuthCache } from "../routes/protected-route"
import { isManager } from "../routes/roles"

// Peer tabs of the session workspace. The Discussion Graph used to be
// reachable only through a toolbar menu item on the overview — a top-level
// route hidden behind a buried entry point. Server load is admin territory
// (same rule as Admin > Server health), so it only appears for managers.
export function SessionTabs() {
    const { sessionId } = useParams()
    const tabs = [
        { label: "Overview", to: `/sessions/${sessionId}/overview` },
        { label: "Devices", to: `/sessions/${sessionId}/devices` },
        { label: "Discussion graph", to: `/sessions/${sessionId}/graph` },
    ]
    if (isManager(getAuthCache())) tabs.push({ label: "Server load", to: `/sessions/${sessionId}/server` })
    return <TabBar label="Session views" tabs={tabs} />
}
