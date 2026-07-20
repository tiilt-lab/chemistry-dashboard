import { useEffect } from "react"
import { useNavigate } from "react-router-dom"

// The one place the "can this account manage things?" question is answered.
// Previously the same `isAdmin || isSuper` boolean was re-derived ad hoc in
// homescreen, users, raters, students and (missing entirely) ops — four
// different enforcement styles across five files.
export interface RoleUser {
    isAdmin?: boolean
    isSuper?: boolean
}

export const isManager = (user?: RoleUser | null): boolean =>
    !!user && (!!user.isAdmin || !!user.isSuper)

// Admin-only pages: bounce non-managers back to /home once the user object is
// known. Returns the boolean so callers can also gate their initial loads.
export function useRequireManager(user?: RoleUser | null): boolean {
    const navigate = useNavigate()
    const ok = isManager(user)
    useEffect(() => {
        if (user && !ok) navigate("/home")
    }, [user, ok, navigate])
    return ok
}
