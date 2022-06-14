import { Routes, Route, BrowserRouter } from 'react-router-dom'
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component'
import {HomeScreen} from '../homescreen/homescreen-component'

function PageRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/home" element={<HomeScreen />} />
            </Routes>
        </BrowserRouter>
    )
}

export {PageRouter}
