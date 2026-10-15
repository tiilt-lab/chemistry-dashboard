import { describe, it, expect } from "vitest"
import { DEFAULT_POD_SETUP, setupTeams, podConfigFromSetup, podSetupProblem, deviceCount, deviceTotal } from "./pod-setup"

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
    it("supports a custom count of teams up to eight, one device per group beyond two", () => {
        const four = { ...DEFAULT_POD_SETUP, enabled: true, teamsPerGroup: 4 }
        expect(setupTeams(four).map((t) => t.name)).toEqual(["Team A", "Team B", "Team C", "Team D"])
        const cfg = podConfigFromSetup(four)
        expect(cfg.group_size).toBe(12)
        expect(cfg.devices_per_group).toBe("group")
        expect(setupTeams({ ...four, teamsPerGroup: 8 }).map((t) => t.name).at(-1)).toBe("Team H")
        expect(setupTeams({ ...four, teamsPerGroup: 9 })).toHaveLength(8)
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

describe("device totals", () => {
    it("counts one device per team only with two teams recording separately", () => {
        const twoTeams = { ...DEFAULT_POD_SETUP, enabled: true, groupCount: 12, devices: "team" }
        expect(deviceCount(twoTeams)).toBe(24)
        expect(deviceCount({ ...twoTeams, devices: "group" })).toBe(12)
        expect(deviceCount({ ...twoTeams, teamsPerGroup: 1 })).toBe(12)
        expect(deviceCount({ ...twoTeams, teamsPerGroup: 3 })).toBe(12)
        expect(deviceCount({ ...twoTeams, groupCount: 0 })).toBe(0)
    })
    it("spells the total out, singular for one", () => {
        expect(deviceTotal(24)).toBe("(24 devices total)")
        expect(deviceTotal(1)).toBe("(1 device total)")
    })
})
