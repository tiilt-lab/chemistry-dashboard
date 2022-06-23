import { Routes, Route, BrowserRouter } from 'react-router-dom'
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component'
import {HomeScreen} from '../homescreen/homescreen-component'
import {JoinPage} from '../byod-join/byod-join-component';
import {ManageKeywordListsComponent} from '../manage-keyword-lists/manage-keyword-lists-component';
import {KeywordListItemsComponent} from '../keyword-list-items/keyword-list-items-component';
import {ProtectedRoute} from './protected-route' 

function PageRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/join" element={<JoinPage />} />
                <Route path='/home' element={<ProtectedRoute component={HomeScreen} />}/>
                <Route path='/keyword-lists' element={<ProtectedRoute component={ManageKeywordListsComponent} />}/>
                <Route path='/keyword-lists/new-keyword-list' element={<ProtectedRoute component={KeywordListItemsComponent}/>}/>
                <Route path='/keyword-lists/:keyword_list_id' element={<ProtectedRoute component={KeywordListItemsComponent}/>}/>
            </Routes>
        </BrowserRouter>
    )
}

export {PageRouter}
