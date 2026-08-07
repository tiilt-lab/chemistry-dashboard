import { useParams } from "react-router-dom"
import { TabBar } from "./tab-bar"

// Peer tabs of the session workspace. The Discussion Graph used to be
// reachable only through a toolbar menu item on the overview — a top-level
// route hidden behind a buried entry point.
export function SessionTabs() {
    const { sessionId } = useParams()
    return (
        <TabBar
            label="Session views"
            tabs={[
                { label: "Overview", to: `/sessions/${sessionId}/overview` },
                { label: "Discussion graph", to: `/sessions/${sessionId}/graph` },
            ]}
        />
    )
}
