// Components
import { AddButtonComponent } from './add-button/add-button.component';
import { AppComponent } from './app.component';
import { ByodJoinComponent } from './byod-join/byod-join.component';
import { ContextMenuComponent } from './components/context-menu/context-menu.component';
import { CreateSessionComponent } from './create-session/create-session.component';
import { DialogComponent } from './dialog/dialog.component';
import { FeaturesComponent } from './features/features.component';
import { FolderSelectComponent } from './components/folder-select/folder-select.component';
import { HeaderComponent } from './header/header.component';
import { HeatMapComponent } from './heat-map/heat-map.component';
import { HomescreenComponent } from './homescreen/homescreen.component';
import { KeywordsComponent } from './keywords/keywords.component';
import { KeywordListItemsComponent } from './keyword-list-items/keyword-list-items.component';
import { LandingPageComponent } from './landing-page/landing-page.component';
import { LoginComponent } from './login/login.component';
import { ManageKeywordListsComponent } from './manage-keyword-lists/manage-keyword-lists.component';
import { PodComponent } from './pod-details/pod.component';
import { PodsComponent } from './pods/pods.component';
import { PodsOverviewComponent } from './pods-overview/pods-overview.component';
import { SectionBoxComponent } from './section-box/section-box.component';
import { SessionsComponent } from './sessions/sessions.component';
import { SessionManagerComponent } from './session-manager/session-manager.component';
import { SessionToolbarComponent } from './session-toolbar/session-toolbar.component';
import { SettingsComponent } from './settings/settings.component';
import { SpinnerComponent } from './spinner/spinner.component';
import { TimelineComponent } from './timeline/timeline.component';
import { TimelineSliderComponent } from './components/timeline-slider/timeline-slider.component';
import { TranscriptsComponent } from './transcripts/transcripts.component';

// Modules
import { BrowserModule } from '@angular/platform-browser';
import { ClickOutsideModule } from 'ng-click-outside';
import { FormsModule } from '@angular/forms';
import { HttpModule } from '@angular/http';
import { NgModule } from '@angular/core';
import { NgSelectModule } from '@ng-select/ng-select';
import { Routing } from './app.routing';

// Services
import { ActiveSessionService } from './services/active-session.service';
import { ApiService } from './services/api.service';
import { AuthService, LoginGuard } from './services/auth.service';
import { DeviceService } from './services/device.service';
import { KeywordService } from './services/keyword.service';
import { SocketService } from './services/socket.service';
import { SessionService } from './services/session.service';
import { DiscussionGraphComponent } from './discussion-graph/discussion-graph.component';

@NgModule({
  declarations: [
    AddButtonComponent,
    AppComponent,
    ByodJoinComponent,
    ContextMenuComponent,
    CreateSessionComponent,
    DialogComponent,
    DiscussionGraphComponent,
    FeaturesComponent,
    FolderSelectComponent,
    HeaderComponent,
    HeatMapComponent,
    HomescreenComponent,
    KeywordsComponent,
    KeywordListItemsComponent,
    LandingPageComponent,
    LoginComponent,
    ManageKeywordListsComponent,
    PodComponent,
    PodsComponent,
    PodsOverviewComponent,
    SectionBoxComponent,
    SessionsComponent,
    SessionManagerComponent,
    SessionToolbarComponent,
    SettingsComponent,
    SpinnerComponent,
    TimelineComponent,
    TimelineSliderComponent,
    TranscriptsComponent
  ],

  imports: [
    BrowserModule,
    Routing,
    HttpModule,
    FormsModule,
    ClickOutsideModule,
    NgSelectModule
  ],
  providers: [
    ActiveSessionService,
    ApiService,
    AuthService,
    DeviceService,
    KeywordService,
    LoginGuard,
    SessionService,
    SocketService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
