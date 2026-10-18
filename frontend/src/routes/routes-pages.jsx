import { lazy, Suspense } from 'react'
import { Routes, Route, BrowserRouter, Navigate } from 'react-router-dom'
import LandingPageComponent from '../landing-page/landing-page-components';
import { LoginPage } from '../login/login-component'
import {HomeScreen} from '../homescreen/homescreen-component'
import {SignupPage} from '../profile-creation/profile-creation-component';
import { RegisterPage } from '../register/register-component'
import { ForgotPasswordPage, ResetPasswordPage } from '../login/password-reset-pages'
import {SessionsComponent} from '../sessions/sessions-component'
import {SessionManagerComponent} from '../session-manager/session-manager-component';
import { AppSpinner } from '../spinner/spinner-component'
import {ProtectedRoute} from './protected-route'
import { AppShell } from '../shell/app-shell'
import { RouteErrorBoundary } from './error-boundary'

// Heavy dashboards (chart.js / d3 / framer-motion / shadcn) are code-split so
// the landing/login/join first load stays small. Each lazy chunk shows the
// shared spinner while it streams in.
const JoinPage = lazy(() => import('../byod-join/byod-join-component').then(m => ({ default: m.JoinPage })))
const StudentSessionDashboard = lazy(() => import('../student-dashboard/student-dashboard-component').then(m => ({ default: m.StudentSessionDashboard })))
const ExpertRatingComponent = lazy(() => import('../expert-rating/expert-rating-component').then(m => ({ default: m.ExpertRatingComponent })))
const CreateSessionComponent = lazy(() => import('../create-session/create-session-component').then(m => ({ default: m.CreateSessionComponent })))
const PodsOverviewComponent = lazy(() => import('../pods-overview/pods-overview-component').then(m => ({ default: m.PodsOverviewComponent })))
const SessionDevicesComponent = lazy(() => import('../session-devices/session-devices-component').then(m => ({ default: m.SessionDevicesComponent })))
const SessionHealthComponent = lazy(() => import('../session-health/session-health-component').then(m => ({ default: m.SessionHealthComponent })))
const DiscussionGraphComponent = lazy(() => import('../discussion-graph/discussion-graph-component').then(m => ({ default: m.DiscussionGraphComponent })))
const SettingsComponent = lazy(() => import('../settings/settings-component').then(m => ({ default: m.SettingsComponent })))
const OpsComponent = lazy(() => import('../ops/ops-component').then(m => ({ default: m.OpsComponent })))
const PodComponent = lazy(() => import('../pod-details/pod-component').then(m => ({ default: m.PodComponent })))
const TranscriptsComponent = lazy(() => import('../transcripts/transcripts-component').then(m => ({ default: m.TranscriptsComponent })))
const TableComponent = lazy(() => import('../table-view/table-component').then(m => ({ default: m.TableComponent })))
const ManageCodingSchemesComponent = lazy(() => import('../coding-schemes/manage-coding-schemes-component').then(m => ({ default: m.ManageCodingSchemesComponent })))
const CodingSchemeEditorComponent = lazy(() => import('../coding-schemes/coding-scheme-editor-component').then(m => ({ default: m.CodingSchemeEditorComponent })))
const StudentsComponent = lazy(() => import('../students/students-component').then(m => ({ default: m.StudentsComponent })))
const StudentProfileComponent = lazy(() => import('../student-profile/student-profile-component').then(m => ({ default: m.StudentProfileComponent })))
const RatersComponent = lazy(() => import('../raters/raters-component').then(m => ({ default: m.RatersComponent })))
const UsersComponent = lazy(() => import('../users/users-component').then(m => ({ default: m.UsersComponent })))

function RouteFallback() {
    return (
        <div className="flex h-full w-full grow items-center justify-center py-24">
            <AppSpinner />
        </div>
    )
}

function PageRouter() {

    return (
        // v7_startTransition keeps the current page on screen while a lazy
        // route chunk loads, instead of flashing the Suspense spinner.
        <BrowserRouter future={{ v7_startTransition: true }}>
            <RouteErrorBoundary>
            <Suspense fallback={<RouteFallback />}>
            <Routes>
                <Route path="/" element={<LandingPageComponent />} />
                <Route path="/login" element={<LoginPage  />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                <Route path="/reset-password" element={<ResetPasswordPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/join" element={<JoinPage />} />
                <Route path="/join/:joinCode" element={<JoinPage />} />
                <Route path="/student/dashboard" element={<StudentSessionDashboard />} />
                <Route path="/student/survey" element={<StudentSessionDashboard />} />
                <Route path="/expert/rating" element={<ExpertRatingComponent />} />
                {/* Signed-in pages share the AppShell layout: persistent left
                    nav rail + content column. Public flows stay outside. */}
                <Route element={<AppShell />}>
                <Route path='/home' element={<ProtectedRoute component={HomeScreen} />}/>
                {/* Keyword lists and topic models left the interface on
                    2026-10-14 (five sessions had ever used a keyword list,
                    none a topic model); old links land on the Library. */}
                <Route path='/keyword-lists/*' element={<Navigate replace to="/coding-schemes" />} />
                <Route path='/sessions' element={<ProtectedRoute component={SessionsComponent}/>}/>
                <Route path='/sessions/new' element={<ProtectedRoute component={CreateSessionComponent}/>} />
                <Route path='sessions/:sessionId' element={<ProtectedRoute component={SessionManagerComponent }/>} >
                    <Route path='' element={<Navigate to="overview"  />} />
                    <Route path='overview' element={<ProtectedRoute component={PodsOverviewComponent}/>} />
                    <Route path='devices' element={<ProtectedRoute component={SessionDevicesComponent}/>} />
                    <Route path='graph' element={<ProtectedRoute component={DiscussionGraphComponent}/>} />
                    <Route path='server' element={<ProtectedRoute component={SessionHealthComponent}/>} />
                    <Route path='pods/:sessionDeviceId' element={<ProtectedRoute component={PodComponent}/>} />
                    <Route path='pods/:sessionDeviceId/transcripts' element={<ProtectedRoute component={TranscriptsComponent}/>} />
                    <Route path='tables/:group' element={<ProtectedRoute component={TableComponent}/>} />
                </Route>
                <Route path='/topic-models' element={<Navigate replace to="/coding-schemes" />} />
                <Route path='/coding-schemes' element={<ProtectedRoute component={ManageCodingSchemesComponent}/>} />
                <Route path='/coding-schemes/new' element={<ProtectedRoute component={CodingSchemeEditorComponent}/>} />
                <Route path='/coding-schemes/:ref' element={<ProtectedRoute component={CodingSchemeEditorComponent}/>} />
                <Route path='/file_upload/*' element={<Navigate replace to="/coding-schemes" />} />
                <Route path='/topic-list/*' element={<Navigate replace to="/coding-schemes" />} />
                {/* The Devices page (physical recorder hardware) is gone.
                    Both paths redirect so existing links and bookmarks land
                    somewhere useful instead of a blank shell. Pods are still
                    managed where they are used: when creating a session, and
                    in Settings. */}
                <Route path='/devices' element={<Navigate replace to="/sessions" />} />
                <Route path='/pods' element={<Navigate replace to="/sessions" />} />
                <Route path='/students' element={<ProtectedRoute component={StudentsComponent}/> } />
                <Route path='/students/:studentId' element={<ProtectedRoute component={StudentProfileComponent}/> } />
                <Route path='/raters' element={<ProtectedRoute component={RatersComponent}/> } />
                <Route path='/people' element={<Navigate replace to="/students" />} />
                <Route path='/library' element={<Navigate replace to="/coding-schemes" />} />
                <Route path='/users' element={<ProtectedRoute component={UsersComponent}/> } />
                <Route path='/settings' element={<ProtectedRoute component={SettingsComponent}/> } />
                <Route path='/ops' element={<ProtectedRoute component={OpsComponent}/> } />
                </Route>
            </Routes>
            </Suspense>
            </RouteErrorBoundary>
        </BrowserRouter>
    )
}

export {PageRouter}
