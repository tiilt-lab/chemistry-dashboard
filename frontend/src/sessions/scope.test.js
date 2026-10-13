import { describe, it, expect } from "vitest"
import { scopeSessions, listedSessions } from "./scope"

const sessions = [
    { id: 1, folder: null },
    { id: 2, folder: 30 },
    { id: 3, folder: 30 },
    { id: 4, folder: 31 },
]

describe("folder scoping", () => {
    it("counts every session at Home and only the folder's own inside a folder", () => {
        expect(scopeSessions(sessions, "")).toHaveLength(4)
        expect(scopeSessions(sessions, null)).toHaveLength(4)
        expect(scopeSessions(sessions, 30).map((s) => s.id)).toEqual([2, 3])
        expect(scopeSessions(sessions, 99)).toEqual([])
        expect(scopeSessions(undefined, 30)).toEqual([])
    })
    it("lists unfiled sessions at Home and the folder's own inside a folder", () => {
        expect(listedSessions(sessions, "").map((s) => s.id)).toEqual([1])
        expect(listedSessions(sessions, 30).map((s) => s.id)).toEqual([2, 3])
        expect(listedSessions(sessions, 31).map((s) => s.id)).toEqual([4])
    })
})
