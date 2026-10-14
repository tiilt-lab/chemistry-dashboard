import { TabBar } from "./tab-bar"

// The Library section: keyword lists, topic models and coding schemes are
// tabs of one configuration area, not unrelated top-level pages.
export function LibraryTabs() {
    return (
        <TabBar
            label="Library"
            tabs={[
                { label: "Keyword lists", to: "/keyword-lists" },
                { label: "Topic models", to: "/topic-models" },
                { label: "Coding schemes", to: "/coding-schemes" },
            ]}
        />
    )
}
