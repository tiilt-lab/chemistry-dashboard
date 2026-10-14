import { TabBar } from "./tab-bar"

// The Library section. Coding schemes are its only tab since keyword lists
// and topic models left the interface (2026-10-14); the bar stays so a
// second kind of library item slots in without a layout change.
export function LibraryTabs() {
    return (
        <TabBar
            label="Library"
            tabs={[
                { label: "Coding schemes", to: "/coding-schemes" },
            ]}
        />
    )
}
