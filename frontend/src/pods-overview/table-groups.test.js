import { describe, it, expect } from "vitest"
import { groupByTable, hasTables } from "./table-groups"

const pod = (id, name, group, side) => ({ id, name, negotiation_group: group, negotiation_side: side })

describe("groupByTable", () => {
    it("keeps an ungrouped session as one unnamed block in order", () => {
        const devices = [pod(1, "B"), pod(2, "A")]
        expect(hasTables(devices)).toBe(false)
        expect(groupByTable(devices, [])).toEqual([
            { group: null, devices: [{ device: devices[0], index: 0 }, { device: devices[1], index: 1 }] },
        ])
    })

    it("sorts tables naturally and laptops by side then name, keeping row numbers", () => {
        const devices = [
            pod(10, "Group 10 Sandy", "Group 10", "Sandy"),
            pod(11, "Group 2 Sandy", "Group 2", "Sandy"),
            pod(12, "Group 2 Pat", "Group 2", "Pat"),
            pod(13, "Hallway", null, null),
            pod(14, "Group 2 Pat 2", "Group 2", "Pat"),
        ]
        expect(hasTables(devices)).toBe(true)
        const tables = groupByTable(devices, ["Pat", "Sandy"])
        expect(tables.map((t) => t.group)).toEqual(["Group 2", "Group 10", null])
        expect(tables[0].devices.map((d) => d.device.id)).toEqual([12, 14, 11])
        expect(tables[0].devices.map((d) => d.index)).toEqual([2, 4, 1])
        expect(tables[2].devices.map((d) => d.device.id)).toEqual([13])
    })
})
