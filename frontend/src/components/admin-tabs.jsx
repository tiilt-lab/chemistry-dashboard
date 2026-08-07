import { TabBar } from "./tab-bar"

// The Admin area: account management, rater assignments, and server health
// present as one guarded section instead of three unrelated pages (one of
// which — /ops — used to be reachable only by typing the URL).
export function AdminTabs() {
    return (
        <TabBar
            label="Administration"
            tabs={[
                { label: "Users", to: "/users" },
                { label: "Raters", to: "/raters" },
                { label: "Server health", to: "/ops" },
            ]}
        />
    )
}
