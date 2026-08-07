import { TabBar } from "./tab-bar"

// The Library section: keyword lists and topic models are two tabs of one
// configuration area, not two unrelated top-level pages.
export function LibraryTabs() {
    return (
        <TabBar
            label="Library"
            tabs={[
                { label: "Keyword lists", to: "/keyword-lists" },
                { label: "Topic models", to: "/topic-models" },
            ]}
        />
    )
}
