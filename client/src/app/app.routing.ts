import { ModuleWithProviders } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { PodsOverviewComponent } from './pods-overview/pods-overview.component';
import { SessionsComponent } from './sessions/sessions.component';
import { ManageKeywordListsComponent } from './manage-keyword-lists/manage-keyword-lists.component';
import { KeywordListItemsComponent } from './keyword-list-items/keyword-list-items.component';
import { PodComponent } from './pod-details/pod.component';
import { HomescreenComponent } from './homescreen/homescreen.component';
import { PodsComponent } from './pods/pods.component';
import { TranscriptsComponent } from './transcripts/transcripts.component';
import { ByodJoinComponent } from './byod-join/byod-join.component';
import { SessionManagerComponent } from './session-manager/session-manager.component';
import { SettingsComponent } from './settings/settings.component';
import { LandingPageComponent } from './landing-page/landing-page.component';
import { LoginGuard } from './services/auth.service';
import { CreateSessionComponent } from './create-session/create-session.component';
import { DiscussionGraphComponent } from './discussion-graph/discussion-graph.component';

const appRoutes: Routes = [
    {
        path: '',
        component: LandingPageComponent
    },
    {
        path: 'login',
        component: LoginComponent
    },
    {
        path: 'join',
        component: ByodJoinComponent
    },
    {
        path: 'homescreen',
        component: HomescreenComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'settings',
        component: SettingsComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'sessions',
        component: SessionsComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'sessions/new',
        component: CreateSessionComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'sessions/:sessionId',
        component: SessionManagerComponent,
        children: [
            {
                path: '',
                redirectTo: 'overview',
                pathMatch: 'full'
            },
            {
                path: 'overview',
                component: PodsOverviewComponent,
                canActivate: [LoginGuard]
            },
            {
                path: 'graph',
                component: DiscussionGraphComponent,
                canActivate: [LoginGuard]
            },
            {
                path: 'pods/:sessionDeviceId',
                component: PodComponent,
                canActivate: [LoginGuard]
            },
            {
                path: 'pods/:sessionDeviceId/transcripts',
                component: TranscriptsComponent,
                canActivate: [LoginGuard]
            }
        ]
    },
    {
        path: '',
        redirectTo: '/homescreen',
        pathMatch: 'full',
        canActivate: [LoginGuard]
    },
    {
        path: 'keyword-lists',
        component: ManageKeywordListsComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'keyword-lists/new-keyword-list',
        component: KeywordListItemsComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'keyword-lists/:keyword-list-id',
        component: KeywordListItemsComponent,
        canActivate: [LoginGuard]
    },
    {
        path: 'pods',
        component: PodsComponent,
        canActivate: [LoginGuard]
    }
];

export const Routing: ModuleWithProviders = RouterModule.forRoot(appRoutes);
