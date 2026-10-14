import { describe, it, expect } from "vitest"
import { slotLinks, slotLinksText } from "./slot-links"

const link = "https://nublinc.com/join/WOLF"

describe("slot links", () => {
    it("is empty without a setup or preset groups", () => {
        expect(slotLinks(null, link)).toEqual([])
        expect(slotLinks({ pod_config: null }, link)).toEqual([])
        expect(slotLinks({ pod_config: { groups: [] } }, link)).toEqual([])
        expect(slotLinks({ pod_config: { groups: ["A"] } }, "")).toEqual([])
    })
    it("makes one link per table and team when each team has a laptop", () => {
        const s = { pod_config: { groups: ["Table 1", "Table 2"], devices_per_group: "team",
                                  teams: [{ name: "Pat", size: 3 }, { name: "Sandy", size: 3 }] } }
        const out = slotLinks(s, link)
        expect(out.map((l) => l.label)).toEqual(["Table 1 · Pat's team", "Table 1 · Sandy's team", "Table 2 · Pat's team", "Table 2 · Sandy's team"])
        expect(out[1].url).toBe("https://nublinc.com/join/WOLF?group=Table%201&team=Sandy")
        expect(slotLinksText(out.slice(0, 1))).toBe("Table 1 · Pat's team: https://nublinc.com/join/WOLF?group=Table%201&team=Pat")
    })
    it("makes one link per table with one laptop per group", () => {
        const s = { pod_config: { groups: ["Left", "Right"], devices_per_group: "group", teams: [] } }
        expect(slotLinks(s, link).map((l) => [l.label, l.url])).toEqual([
            ["Left", "https://nublinc.com/join/WOLF?group=Left"],
            ["Right", "https://nublinc.com/join/WOLF?group=Right"],
        ])
    })
})
