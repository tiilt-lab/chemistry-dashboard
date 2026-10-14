// The create-session form's pod setup: how a breakout group is composed and
// which device records what. Team names default to Team A, Team B, … and
// are renamed by the instructor (the code knows no case's sides). One team
// (the whole group), two, or a custom count of three or more, up to eight
// (the server's limit); one device per team needs exactly two.
export const MAX_TEAMS = 8
export const MIN_CUSTOM_TEAMS = 3
const LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"]

export const DEFAULT_POD_SETUP = {
    enabled: false,
    groupCount: 10,
    groupPrefix: "Group",
    teamsPerGroup: 2,
    groupSize: 6,
    teams: LETTERS.map((letter) => ({ name: `Team ${letter}`, size: 3 })),
    devices: "team",
}

// The teams in play for a setup: the first teamsPerGroup of them (none
// below two).
export function setupTeams(setup) {
    const n = setup && setup.teamsPerGroup >= 2 ? Math.min(setup.teamsPerGroup, MAX_TEAMS) : 0
    return (setup && Array.isArray(setup.teams) ? setup.teams : []).slice(0, n)
}

// What the API gets for the form's pod setup (null when it is off).
export function podConfigFromSetup(setup) {
    if (!setup || !setup.enabled) return null
    const teams = setupTeams(setup)
    return {
        teams,
        group_size: teams.length ? teams.reduce((sum, t) => sum + t.size, 0) : setup.groupSize,
        devices_per_group: teams.length === 2 ? setup.devices : "group",
        group_count: setup.groupCount,
        group_prefix: setup.groupPrefix,
    }
}

// Why the setup cannot be sent yet, or null.
export function podSetupProblem(setup) {
    if (!setup || !setup.enabled) return null
    const names = setupTeams(setup).map((t) => (t.name || "").trim())
    if (names.some((n) => !n)) return "Name every team in the pod setup."
    if (new Set(names.map((n) => n.toLowerCase())).size !== names.length) return "Teams need different names."
    if (!(setup.groupPrefix || "").trim()) return "Say what the groups are called (for example Group or Table)."
    return null
}
