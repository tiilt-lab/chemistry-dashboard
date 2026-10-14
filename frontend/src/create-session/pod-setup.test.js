import { describe, it, expect } from "vitest"
import { DEFAULT_POD_SETUP, setupTeams, podConfigFromSetup, podSetupProblem } from "./pod-setup"

describe("pod setup", () => {
    it("defaults to Team A / Team B, three a side, one device per team, and is valid as is", () => {
        const on = { ...DEFAULT_POD_SETUP, enabled: true }
        expect(setupTeams(on).map((t) => t.name)).toEqual(["Team A", "Team B"])
        expect(podSetupProblem(on)).toBeNull()
        expect(podConfigFromSetup(on)).toEqual({
            teams: [{ name: "Team A", size: 3 }, { name: "Team B", size: 3 }],
            group_size: 6,
            devices_per_group: "team",
            group_count: 10,
            group_prefix: "Group",
        })
        expect(podConfigFromSetup(DEFAULT_POD_SETUP)).toBeNull()
    })
    it("supports up to four teams, one device per group beyond two", () => {
        const four = { ...DEFAULT_POD_SETUP, enabled: true, teamsPerGroup: 4 }
        expect(setupTeams(four).map((t) => t.name)).toEqual(["Team A", "Team B", "Team C", "Team D"])
        const cfg = podConfigFromSetup(four)
        expect(cfg.group_size).toBe(12)
        expect(cfg.devices_per_group).toBe("group")
        expect(setupTeams({ ...four, teamsPerGroup: 9 })).toHaveLength(4)
        const none = { ...DEFAULT_POD_SETUP, enabled: true, teamsPerGroup: 1, groupSize: 5 }
        expect(podConfigFromSetup(none)).toMatchObject({ teams: [], group_size: 5, devices_per_group: "group" })
    })
    it("refuses blank or duplicate team names and a blank group label", () => {
        const on = { ...DEFAULT_POD_SETUP, enabled: true }
        const rename = (i, name) => ({ ...on, teams: on.teams.map((t, j) => (j === i ? { ...t, name } : t)) })
        expect(podSetupProblem(rename(1, " "))).toBe("Name every team in the pod setup.")
        expect(podSetupProblem(rename(1, "team a"))).toBe("Teams need different names.")
        expect(podSetupProblem({ ...on, groupPrefix: "" })).toBe("Say what the groups are called (for example Group or Table).")
        expect(podSetupProblem({ ...rename(1, "Sandy"), teams: rename(1, "Sandy").teams.map((t, j) => (j === 0 ? { ...t, name: "Pat" } : t)) })).toBeNull()
    })
})
