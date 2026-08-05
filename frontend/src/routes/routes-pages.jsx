import { Routes, Route, BrowserRouter, Navigate } from 'react-router-dom';
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component';
import {HomeScreen} from '../homescreen/homescreen-component';
import {JoinPage} from '../byod-join/byod-join-component';
import {SessionsComponent} from '../sessions/sessions-component';
import {CreateSessionComponent} from '../create-session/create-session-component';
import {PodsOverviewComponent} from '../pods-overview/pods-overview-component';
import {SessionManagerComponent} from '../session-manager/session-manager-component';
import {DiscussionGraphComponent} from '../discussion-graph/discussion-graph-component';
import { SettingsComponent } from '../settings/settings-component';
import { PodComponent } from '../pod-details/pod-component';
import {TranscriptsComponent} from '../transcripts/transcripts-component';
import {PodsComponent} from '../pods/pods-component';
import {ProtectedRoute} from './protected-route';
import {SessionFeedbackForm} from "../feedback-form/session-feedback-form";
import {RagSearchComponent} from '../rag-search/RagSearchComponent';
import { AgentChatPanel, V3ChatPanel, V7ChatPanel } from '../components/agent-chat';
import BaselineAgentChatPanel from '../components/agent-chat/BaselineAgentChatPanel';
import { ExpertAgentRating } from '../expert-agent-rating/expert-agent-rating';
import AppLayout from '../components/app-layout/AppLayout';

function PageRouter() {

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage  />} />
                <Route path="/join" element={<JoinPage />} />
                <Route path='/home' element={<ProtectedRoute component={HomeScreen} />}/>
                <Route path='/sessions' element={<ProtectedRoute component={SessionsComponent}/>}/>
                <Route path='/sessions/new' element={<ProtectedRoute component={CreateSessionComponent}/>} />
                <Route path='sessions/:sessionId' element={<ProtectedRoute component={SessionManagerComponent }/>} >
                    <Route path='' element={<Navigate to="overview"  />} />
                    <Route path='overview' element={<ProtectedRoute component={PodsOverviewComponent}/>} />
                    <Route path='graph' element={<ProtectedRoute component={DiscussionGraphComponent}/>} />
                    <Route path='pods/:sessionDeviceId' element={<ProtectedRoute component={PodComponent}/>} />
                    <Route path='pods/:sessionDeviceId/transcripts' element={<ProtectedRoute component={TranscriptsComponent}/>} />
                </Route>
                <Route path='/pods' element={<ProtectedRoute component={PodsComponent}/> } />
                <Route path='/settings' element={<ProtectedRoute component={SettingsComponent}/> } />
                <Route path="/feedback-form/:sessionId" element={<SessionFeedbackForm />} />
                <Route path='/discover' element={<ProtectedRoute component={RagSearchComponent} />}/>
                <Route path='/chat-baseline' element={<ProtectedRoute component={BaselineAgentChatPanel} />}/>
                <Route path='/chat-v3' element={<ProtectedRoute component={V3ChatPanel} />}/>
                <Route path='/chat-v7' element={<ProtectedRoute component={V7ChatPanel} />}/>
                <Route path='/expert-agent-rating' element={<ExpertAgentRating />} />
                <Route path='/transcripts/device/:deviceId' element={<TranscriptsComponent />} />
                {/* New two-panel discussion dashboard */}
                <Route path='/app' element={<ProtectedRoute component={AppLayout} />} />
                <Route path='/app/:deviceId' element={<ProtectedRoute component={AppLayout} />} />
                <Route path='/app/:deviceId/:tab' element={<ProtectedRoute component={AppLayout} />} />
            </Routes>
        </BrowserRouter>
    )
}

export {PageRouter}
