import { Navigate, useLocation, } from "react-router-dom";
import { useState } from "react";
import { AuthService } from "../services/auth-service";

function ProtectedRoute({ component: Component, ...rest }) {
    const location = useLocation();
    const [isauth, setIsAuth] = useState(0);
    if (isauth !== 0) {
        if (isauth.status === 200) {
            return <Component />
        } else {
            return <Navigate replace={true} to="/login" state={{ from: `${location.pathname}${location.search}` }} />
        }
    }

    new AuthService().me(setIsAuth);
}

export { ProtectedRoute }