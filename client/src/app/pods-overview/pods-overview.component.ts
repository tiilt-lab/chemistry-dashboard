import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { SessionService } from '../services/session.service';
import { ActiveSessionService } from '../services/active-session.service';
import { DeviceService } from '../services/device.service';
import 'rxjs/add/operator/finally';

enum Forms {
    Passcode = 1,
    AddDevice
}

@Component({
    selector: 'app-pods-overview',
    templateUrl: './pods-overview.component.html',
    styleUrls: ['./pods-overview.component.scss']
})

export class PodsOverviewComponent implements OnInit, OnDestroy {
    sessionClosing = false;
    openingDialog = false;
    sessionDevices: any[] = [];
    session: any;
    selectedSessionDevice: any;
    subscriptions: any[] = [];
    devices: any[];
    currentForm: Forms = null;
    forms = Forms;

    POD_ON_COLOR = '#FF6655';
    POD_OFF_COLOR = '#D0D0D0';
    GLOW_COLOR = '#ffc3bd';

    constructor(private router: Router,
                private route: ActivatedRoute,
                private deviceService: DeviceService,
                private sessionService: SessionService,
                private activeSessionService: ActiveSessionService) { }

    ngOnInit() {
        const sessionSub = this.activeSessionService.getSession().subscribe(e => {
            this.session = e;
        });
        const deviceSub = this.activeSessionService.getSessionDevices().subscribe(e => {
            this.sessionDevices = e;
        });
        this.subscriptions.push(sessionSub, deviceSub);
    }

    ngOnDestroy() {
        this.subscriptions.map(sub => sub.unsubscribe());
    }

    goToDevice(sessionDevice) {
        this.router.navigate(['sessions', this.session.id, 'pods', sessionDevice.id]);
    }

    onSessionClosing(isClosing: boolean) {
        this.sessionClosing = isClosing;
    }

    navigateToSessions() {
        this.router.navigate(['sessions'], {queryParams: {folder: this.session.folder}});
    }

    openDialog(form: Forms) {
        if (form === this.forms.AddDevice) {
            this.deviceService.getDevices(false, true, false, true).subscribe(devices => {
                this.devices = devices;
                this.currentForm = form;
            });
        } else if (form === this.forms.Passcode && this.session.end_date == null) {
            this.currentForm = form;
        }
    }

    getPasscode() {
        if (this.session.end_date) {
            return 'CLOSED';
        } else if (this.session.passcode == null) {
            return 'LOCKED';
        } else {
            return this.session.passcode;
        }
    }

    addPodToSession(deviceId: number) {
        this.sessionService.addPodToSession(this.session.id, deviceId).subscribe(response => {
            this.closeDialog();
        });
    }

    setPasscodeState(state: string) {
        this.sessionService.setPasscodeStatus(this.session.id, state).subscribe(response => {
            this.closeDialog();
        });
    }

    exportSession() {
        this.sessionService.downloadSessionReport(this.session.id, this.session.title).subscribe(x => {
            console.log('Download successful.');
        }, error => {
            alert('Failed to download session report.');
        });
    }

    closeDialog() {
        this.currentForm = null;
    }

    goToGraph() {
        this.router.navigate(['sessions/' + this.session.id + '/graph']);
    }
}
