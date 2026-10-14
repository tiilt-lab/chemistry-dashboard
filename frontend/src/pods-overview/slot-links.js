// Join links for every slot of a session's pod setup, for printing or
// pasting into a slide: /join/CODE?group=Table%203&team=Pat prefills the
// table and team so a laptop joins with one click. [] when the session has
// no setup or no preset groups (the plain join link covers it).
export function slotLinks(session, joinLink) {
    const cfg = session && session.pod_config
    if (!cfg || !joinLink || !Array.isArray(cfg.groups) || cfg.groups.length === 0) return []
    const teams = Array.isArray(cfg.teams) ? cfg.teams : []
    const teamed = cfg.devices_per_group === "team" && teams.length >= 2
    const out = []
    for (const g of cfg.groups) {
        if (teamed) {
            for (const t of teams) {
                out.push({
                    group: g,
                    team: t.name,
                    label: `${g} · ${t.name}'s team`,
                    url: `${joinLink}?group=${encodeURIComponent(g)}&team=${encodeURIComponent(t.name)}`,
                })
            }
        } else {
            out.push({ group: g, team: null, label: g, url: `${joinLink}?group=${encodeURIComponent(g)}` })
        }
    }
    return out
}

// One line per slot, for "Copy all".
export function slotLinksText(links) {
    return (links || []).map((l) => `${l.label}: ${l.url}`).join("\n")
}
