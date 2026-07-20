import { describe, it, expect } from "vitest"
import { isManager } from "./roles"

// Mirrors UserModel's getters: role drives isAdmin/isSuper.
const user = (role) => ({ isAdmin: role === "admin", isSuper: role === "super" })

describe("isManager", () => {
    it("admin and super manage", () => {
        expect(isManager(user("admin"))).toBe(true)
        expect(isManager(user("super"))).toBe(true)
    })
    it("plain users, null, and undefined do not", () => {
        expect(isManager(user("user"))).toBe(false)
        expect(isManager(null)).toBe(false)
        expect(isManager(undefined)).toBe(false)
    })
})
