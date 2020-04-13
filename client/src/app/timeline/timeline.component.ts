import { Component, Input, Output, EventEmitter, DoCheck, OnInit, OnDestroy } from '@angular/core';
import { Observable } from 'rxjs/Observable';
import { SessionModel } from '../models/session';
import { TranscriptModel } from '../models/transcript';
import { formatSeconds } from '../globals';

const TIMELINE_LEFT = 16;
const TIMELINE_WIDTH = 341;
const MIN_UTTERANCE_WIDTH = 1;

@Component({
  selector: 'app-timeline',
  templateUrl: './timeline.component.html',
  styleUrls: ['./timeline.component.scss']
})
export class TimelineComponent {
    @Input('session') session: SessionModel;
    @Input('transcripts')
    set setTranscripts(value: any) {
        this._transcripts = value;
        this.refreshTimeline();
    }
    @Input('start')
    set setStart(value: any) {
        this._start = value;
        if (this._start === 0) {
            this.startText = 'Start';
        } else {
            this.startText = formatSeconds(this._start);
        }
        this.refreshTimeline();
    }
    @Input('end')
    set setEnd(value: any) {
        this._end = value;
        if (this._end === this.session.length) {
            this.endText = (this.session.recording) ? 'Now' : 'End';
        } else {
            this.endText = formatSeconds(this._end);
        }
        this.refreshTimeline();
    }
    @Output() clickedTimeline = new EventEmitter<Object>();

    _transcripts: TranscriptModel[] = [];
    displayTranscripts = [];
    previousTranscriptCount = 0;
    startText = 'Start';
    endText = 'Now';
    _start: number;
    _end: number;

    constructor() { }

    refreshTimeline() {
        const duration = this._end - this._start;
        this.displayTranscripts = [];
        for (const transcript of this._transcripts) {
            const pct_start = (transcript.start_time - this._start) / duration;
            const pct_length = transcript.length / duration;
            const displayTranscript = {};
            displayTranscript['transcript'] = transcript;
            displayTranscript['left'] = pct_start * TIMELINE_WIDTH + TIMELINE_LEFT;
            displayTranscript['width'] = Math.min(Math.max(pct_length * TIMELINE_WIDTH,
                MIN_UTTERANCE_WIDTH), TIMELINE_WIDTH * (1 - pct_start));
            this.displayTranscripts.push(displayTranscript);
        }
    }

    openTranscriptDialog(transcript: any) {
        this.clickedTimeline.emit(transcript);
    }
}
