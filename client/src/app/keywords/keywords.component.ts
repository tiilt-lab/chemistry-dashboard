import { Component, OnInit, Input } from '@angular/core';
import { Router } from '@angular/router';
import { Observable } from 'rxjs/Observable';
import { SessionModel } from '../models/session';
import { SessionDeviceModel } from '../models/session-device';
import { TranscriptModel } from '../models/transcript';
import { formatSeconds, similarityToRGB } from '../globals';

@Component({
  selector: 'app-keywords',
  templateUrl: './keywords.component.html',
  styleUrls: ['./keywords.component.scss']
})
export class KeywordsComponent {
  _transcripts: TranscriptModel[] = [];
  displayKeywords = [];
  showGraph = false;
  keywordPoints: any;
  timelineWidth = 240;
  _start: number;
  _end: number;

  @Input('session') session: SessionModel;
  @Input('sessionDevice') sessionDevice: SessionDeviceModel;
  @Input('transcripts')
  set setTranscripts(value: any) {
    this._transcripts = value;
    this.refresh();
  }
  @Input('start')
  set setStart(value: any) {
    this._start = value;
    this.refresh();
  }
  @Input('end')
  set setEnd(value: any) {
    this._end = value;
    this.refresh();
  }

  constructor(private router: Router) {}

  toggleGraph() {
    this.showGraph = !this.showGraph;
    this.refresh();
  }

  refresh() {
    if (this.showGraph) {
      this.refreshTimeline();
    } else {
      this.refreshKeywords();
    }
  }

  // --------
  // Text
  // --------

  refreshKeywords() {
    this.displayKeywords = [];
    for (const transcript of this._transcripts) {
      const words = new Set(transcript.keywords.map(k => k.word));
      words.forEach(word => {
        const highestSimilarity = Math.max(...transcript.keywords.filter(k => k.word === word).map(k => k.similarity));
        this.displayKeywords.push({'word': word, 'color': similarityToRGB(highestSimilarity), 'transcript_id': transcript.id});
      });
    }
  }

  showKeywordContext(transcriptId: any) {
    this.router.navigate(['sessions', this.session.id, 'pods', this.sessionDevice.id, 'transcripts'], {queryParams: {index: transcriptId}});
  }

  // --------
  // Graph
  // --------

  refreshTimeline() {
    this.keywordPoints = {};
    for (const keyword of this.session.keywords) {
      this.keywordPoints[keyword] = [];
    }

    for (const transcript of this._transcripts) {
      const duration = this._end - this._start;
      const keywordTracker = {};
      for (const keywordUsage of transcript.keywords) {
        const transcriptText = transcript.transcript;
        const word = keywordUsage.word;
        if (keywordUsage.word in keywordTracker) {
          keywordTracker[keywordUsage.word]++;
        } else {
          keywordTracker[keywordUsage.word] = 0;
        }
        const keywordIndex = keywordTracker[keywordUsage.word];
        const tPos = (transcriptText.indexOf(word, keywordIndex) / transcriptText.length) * transcript.length;
        const pos = (((transcript.start_time + tPos) - this._start) / duration) * this.timelineWidth;
        this.keywordPoints[keywordUsage.keyword].push({
          'x': pos,
          'color': similarityToRGB(keywordUsage.similarity),
          'transcript_id': transcript.id
        });
      }
    }
  }

  getSubstringIndex(str, substring, n) {
    let times = 0, index = null;

    while (times < n && index !== -1) {
        index = str.indexOf(substring, index + 1);
        times++;
    }

    return index;
  }
}

