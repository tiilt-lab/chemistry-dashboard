import { Component, Input, Output, OnInit, OnDestroy, EventEmitter} from '@angular/core';
import { Router } from '@angular/router';
import { SessionService } from '../services/session.service';
import { SessionModel } from '../models/session';

@Component({
  selector: 'app-session-toolbar',
  templateUrl: './session-toolbar.component.html',
  styleUrls: ['./session-toolbar.component.scss']
})
export class SessionToolbarComponent implements OnInit, OnDestroy {
    @Input('session') session: SessionModel;
    @Output() closingSession = new EventEmitter<boolean>();
    timeText: string;
    sessionEnding = false;
    intervalId: any;

    constructor(private router: Router,
                private sessionService: SessionService ) { }

    ngOnInit() {
        this.intervalId = setInterval(() => {
            this.updateTime();
            if (!this.session.recording) {
                clearInterval(this.intervalId);
            }
        }, 1000);
        this.updateTime();
    }

    ngOnDestroy() {
        clearInterval(this.intervalId);
    }

    updateTime() {
        // doesn't currently support displaying hours
        const m = Math.floor(this.session.length / 60);
        const s = Math.floor(this.session.length - m * 60);
        let secs_text: string;
        if (s < 10) {
          secs_text = '0' + s;
        } else {
          secs_text = '' + s;
        }
        this.timeText = m + ':' + secs_text;
    }

    onEndSession() {
        this.sessionEnding = true;
        this.closingSession.emit(true);
        this.sessionService.endSession(this.session.id).subscribe(e => {
            this.router.navigate(['sessions'], {queryParams: {folder: this.session.folder}});
            this.sessionEnding = false;
        });
    }

    closeEndDialog() {
        this.sessionEnding = false;
    }
}
