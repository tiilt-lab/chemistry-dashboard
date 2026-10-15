import { describe, it, expect } from "vitest"
import { fmtUptime, fmtGb, cpuPercent, healthVerdict } from "./health-format"

describe("health formatting", () => {
    it("uptime and gigabytes", () => {
        expect(fmtUptime(3725)).toBe("1h 2m")
        expect(fmtUptime(59)).toBe("0m")
        expect(fmtUptime(null)).toBe("—")
        expect(fmtGb(35840, 49152)).toBe("35.0 / 48 GB")
        expect(fmtGb(null, 1)).toBe("—")
    })
    it("cpu percent from the 1-minute load over the cores, capped at 100", () => {
        expect(cpuPercent({ load_1: 4, cores: 16 })).toBe(25)
        expect(cpuPercent({ load_1: 40, cores: 16 })).toBe(100)
        expect(cpuPercent(null)).toBeNull()
    })
    it("the verdict trips on the worst problem first, judging GPU and disk on what is left", () => {
        const ok = { services: { a: { active: "active" } }, gpu: { mem_used_mb: 39200, mem_total_mb: 49152, mem_pct: 80 }, disk: { used_pct: 83, free_gb: 125 }, host_ram: { used_pct: 60 }, cpu: { load_1: 1, cores: 8 } }
        expect(healthVerdict(ok)).toMatchObject({ tone: "teal" })
        expect(healthVerdict({ ...ok, gpu: { mem_used_mb: 44000, mem_total_mb: 49152 } })).toMatchObject({ tone: "orange" })
        expect(healthVerdict({ ...ok, gpu: { mem_used_mb: 46500, mem_total_mb: 49152 } })).toMatchObject({ tone: "danger" })
        expect(healthVerdict({ ...ok, disk: { used_pct: 95, free_gb: 30 } })).toMatchObject({ tone: "orange" })
        expect(healthVerdict({ ...ok, disk: { used_pct: 99, free_gb: 5 } })).toMatchObject({ tone: "danger" })
        expect(healthVerdict({ ...ok, services: { audio: { active: "failed" } }, disk: { free_gb: 5 } })).toMatchObject({ tone: "danger", text: "Service down: audio" })
        expect(healthVerdict({ ...ok, cpu: { load_1: 9, cores: 8 } })).toMatchObject({ tone: "orange" })
        expect(healthVerdict(null)).toBeNull()
    })
})
