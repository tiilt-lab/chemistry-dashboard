import { Routes, Route, BrowserRouter } from 'react-router-dom'
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component'
import {HomeScreen} from '../homescreen/homescreen-component'
import {JoinPage} from '../byod-join/byod-join-component';
import {ProtectedRoute} from './protected-route' 

function PageRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/join" element={<JoinPage />} />
                <Route path='/home' element={<ProtectedRoute component={HomeScreen} />}/>
            </Routes>
        </BrowserRouter>
    )
}

export {PageRouter}
