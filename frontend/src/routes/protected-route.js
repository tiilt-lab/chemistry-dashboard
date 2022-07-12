import { Navigate, useLocation, } from "react-router-dom";
import { useState } from "react";
import { AuthService } from "../services/auth-service";

function ProtectedRoute({component: Component, ...rest }) {
    const location = useLocation();
    const [isauth, setIsAuth] = useState(null);
    
    if (isauth !== null) {
        if(isauth === 'cors error'){
            return <Navigate replace={true} to="/login" state={{ from: `${location.pathname}${location.search}` }} /> 
        }else if (Object.keys(isauth).length !== 0) {
            return <Component userdata= {isauth} />
        } else {
            return <Navigate replace={true} to="/login" state={{ from: `${location.pathname}${location.search}` }} />
        }
    }

    new AuthService().me(setIsAuth);
}

export { ProtectedRoute }