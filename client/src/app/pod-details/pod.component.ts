import { Component, Input, OnInit, OnDestroy, ElementRef, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable } from 'rxjs/Observable';
import { DeviceService } from '../services/device.service';
import { SessionService } from '../services/session.service';
import { ActiveSessionService } from '../services/active-session.service';
import { SessionModel } from '../models/session';
import { DeviceModel } from '../models/device';
import { TranscriptModel } from '../models/transcript';
import { KeywordUsageModel } from '../models/keyword-usage';

enum Forms {
    Transcript = 1,
    RemoveDevice,
    Options
}

@Component({
    selector: 'app-pod',
    templateUrl: './pod.component.html',
    styleUrls: ['./pod.component.scss']
})

export class PodComponent implements OnInit, OnDestroy {

    sessionDeviceId: any;
    sessionDevice: any;
    session: any;
    transcripts: any[] = [];
    displayTranscripts: any[] = [];
    currentTranscript: any;
    forms = Forms;
    currentForm: Forms = null;
    sessionClosing = false;
    subscriptions: any[] = [];
    deleteDeviceToggle = false;
    timeRange: any[] = [0, 1];
    startTime: number;
    endTime: number;
    intervalId: any;

    constructor(private router: Router,
                private route: ActivatedRoute,
                private deviceService: DeviceService,
                private sessionService: SessionService,
                private activeSessionService: ActiveSessionService) { }

    ngOnInit() {
        this.route.params.subscribe(params => {
            this.sessionDeviceId = +params['sessionDeviceId'];
            const sessionSub = this.activeSessionService.getSession().subscribe(e => {
                this.session = e;
            });
            const deviceSub = this.activeSessionService.getSessionDevice(this.sessionDeviceId).subscribe(e => {
                if (e) {
                    this.sessionDevice = e;
                }
            });
            const transcriptSub = this.activeSessionService.getSessionDeviceTranscripts(this.sessionDeviceId).subscribe(e => {
                this.transcripts = e;
                this.setRange(this.timeRange);
            });
            this.subscriptions.push(sessionSub, deviceSub, transcriptSub);
        });

        // Refresh based on timeslider.
        this.intervalId = setInterval(() => {
            this.setRange(this.timeRange);
            if (!this.session.recording) {
                clearInterval(this.intervalId);
            }
        }, 2000);
        this.setRange(this.timeRange);
    }

    ngOnDestroy() {
        this.subscriptions.map(sub => sub.unsubscribe());
        clearInterval(this.intervalId);
    }

    setRange(values: any[]) {
        this.timeRange = values;
        this.startTime = Math.round(this.session.length * values[0] * 100) / 100;
        this.endTime = Math.round(this.session.length * values[1] * 100) / 100;
        this.generateDispalyTranscripts();
    }

    generateDispalyTranscripts() {
        this.displayTranscripts = this.transcripts.filter(t => t.start_time >= this.startTime && t.start_time <= this.endTime);
    }

    navigateToSession() {
        this.router.navigate(['sessions', this.session.id]);
    }

    onSessionClosing(isClosing: boolean) {
        this.sessionClosing = isClosing;
    }

    seeAllTranscripts() {
        this.router.navigate(['sessions', this.session.id, 'pods', this.sessionDeviceId, 'transcripts'],
                            {queryParams: {index: this.currentTranscript.id}});
    }

    get loading(): boolean {
        return (this.session == null || this.transcripts == null);
    }

    removeDeviceFromSession(deleteDevice: boolean = false) {
        this.sessionService.removeDeviceFromSession(this.session.id, this.sessionDeviceId, deleteDevice).subscribe(response => {
            this.closeDialog();
            if (deleteDevice) {
                this.navigateToSession();
            }
        });
    }

    onClickedTimeline(transcript) {
        this.currentForm = this.forms.Transcript;
        this.currentTranscript = transcript;
    }

    openDialog(form: any) {
        this.deleteDeviceToggle = false;
        this.currentForm = form;
    }

    closeDialog() {
        this.currentForm = null;
    }
}
