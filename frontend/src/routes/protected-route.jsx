import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { AuthService } from "../services/auth-service";

// Session-scoped auth cache. Every navigation used to block on a fresh
// /api/v1/me round trip while rendering NOTHING — the blank flash before the
// spinner before the page. After the first successful check, later
// navigations render immediately from the cache; /me still re-runs in the
// background and bounces the user to /login if the session has died.
let cachedUser = null;
export const clearAuthCache = () => { cachedUser = null; };

function ProtectedRoute({ component: Component }) {
    const location = useLocation();
    const [isauth, setIsAuth] = useState(cachedUser);

    useEffect(() => {
        new AuthService().me((result) => {
            const ok =
                result &&
                result !== "cors error" &&
                Object.keys(result).length !== 0;
            cachedUser = ok ? result : null;
            setIsAuth(ok ? result : "denied");
        });
    }, []);

    if (isauth === null) return null; // first load: wait for /me
    if (isauth === "denied")
        return (
            <Navigate
                replace={true}
                to="/login"
                state={{ from: `${location.pathname}${location.search}` }}
            />
        );
    return <Component userdata={isauth} />;
}

export { ProtectedRoute };
