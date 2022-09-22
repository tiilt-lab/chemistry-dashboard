import { Routes, Route, BrowserRouter, Navigate } from 'react-router-dom'
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component'
import {HomeScreen} from '../homescreen/homescreen-component'
import {JoinPage} from '../byod-join/byod-join-component';
import {ManageKeywordListsComponent} from '../manage-keyword-lists/manage-keyword-lists-component';
import {KeywordListItemsComponent} from '../keyword-list-items/keyword-list-items-component';
import {SessionsComponent} from '../sessions/sessions-component'
import {CreateSessionComponent} from '../create-session/create-session-component'
import {PodsOverviewComponent} from '../pods-overview/pods-overview-component'
import {SessionManagerComponent} from '../session-manager/session-manager-component';
import {DiscussionGraphComponent} from '../discussion-graph/discussion-graph-component'
import {FileUploadComponent} from '../file-upload/file-upload-component'
import { SettingsComponent } from '../settings/settings-component';
import { PodComponent } from '../pod-details/pod-component';
import {TranscriptsComponent} from '../transcripts/transcripts-component'
import {PodsComponent} from '../pods/pods-component'
import {ProtectedRoute} from './protected-route'

function PageRouter() {
    
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage  />} /> 
                <Route path="/join" element={<JoinPage />} />
                <Route path="/join/:resetId" element={<JoinPage />} />
                <Route path='/home' element={<ProtectedRoute component={HomeScreen} />}/>
                <Route path='/keyword-lists' element={<ProtectedRoute  component={ManageKeywordListsComponent} />}/>
                <Route path='/keyword-lists/new' element={<ProtectedRoute  component={KeywordListItemsComponent}/>}/>
                <Route path='/keyword-lists/:keyword_list_id' element={<ProtectedRoute  component={KeywordListItemsComponent}/>}/>
                <Route path='/sessions' element={<ProtectedRoute component={SessionsComponent}/>}/>
                <Route path='/sessions/new' element={<ProtectedRoute component={CreateSessionComponent}/>} />
                <Route path='sessions/:sessionId' element={<ProtectedRoute component={SessionManagerComponent }/>} >
                    <Route path='' element={<Navigate to="overview"  />} />
                    <Route path='overview' element={<ProtectedRoute component={PodsOverviewComponent}/>} />
                    <Route path='graph' element={<ProtectedRoute component={DiscussionGraphComponent}/>} />
                    <Route path='pods/:sessionDeviceId' element={<ProtectedRoute component={PodComponent}/>} />
                    <Route path='pods/:sessionDeviceId/transcripts' element={<ProtectedRoute component={TranscriptsComponent}/>} />
                </Route> 
                <Route path='/file_upload' element={<ProtectedRoute component={FileUploadComponent}/>} />
                <Route path='/pods' element={<ProtectedRoute component={PodsComponent}/> } />
                <Route path='/settings' element={<ProtectedRoute component={SettingsComponent}/> } />
            </Routes>
        </BrowserRouter>
    )
}

export {PageRouter}
