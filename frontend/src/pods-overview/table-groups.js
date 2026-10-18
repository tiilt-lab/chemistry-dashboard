// The pods overview grouped by breakout table. A table is a negotiation
// group (the laptops sharing device.negotiation_group); laptops without a
// group follow, ungrouped. Groups sort naturally ("Group 2" before
// "Group 10"), laptops inside a group by side order then name.

function naturalKey(text) {
    return String(text || "")
        .split(/(\d+)/)
        .map((part) => (/^\d+$/.test(part) ? part.padStart(8, "0") : part.toLowerCase()))
        .join("")
}

// devices: the session's pods as the overview lists them (each keeps its
// position for the row number); teamNames: the session's side order.
// Returns [{group, devices: [{device, index}]}], group null for the rest.
export function groupByTable(devices, teamNames) {
    const sides = teamNames || []
    const groups = new Map()
    const rest = []
    ;(devices || []).forEach((device, index) => {
        const group = device && device.negotiation_group
        if (!group) {
            rest.push({ device, index })
            return
        }
        if (!groups.has(group)) groups.set(group, [])
        groups.get(group).push({ device, index })
    })
    const sideRank = (d) => {
        const i = sides.indexOf(d.negotiation_side)
        return i >= 0 ? i : sides.length
    }
    const tables = Array.from(groups.keys())
        .sort((a, b) => (naturalKey(a) < naturalKey(b) ? -1 : naturalKey(a) > naturalKey(b) ? 1 : 0))
        .map((group) => ({
            group,
            devices: groups.get(group).slice().sort((a, b) =>
                sideRank(a.device) - sideRank(b.device) ||
                naturalKey(a.device.name).localeCompare(naturalKey(b.device.name)) ||
                a.index - b.index),
        }))
    if (rest.length) tables.push({ group: null, devices: rest })
    return tables
}

// True when the overview should show table headers at all.
export function hasTables(devices) {
    return (devices || []).some((d) => d && d.negotiation_group)
}
