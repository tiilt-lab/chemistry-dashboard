import { Component, OnInit, OnDestroy, ViewChildren, ElementRef, QueryList } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ActiveSessionService } from '../services/active-session.service';
import { similarityToRGB } from '../globals';

enum Forms {
  Keyword = 1,
  Options
}

@Component({
  selector: 'app-transcripts',
  templateUrl: './transcripts.component.html',
  styleUrls: ['./transcripts.component.scss']
})
export class TranscriptsComponent implements OnInit, OnDestroy {

  @ViewChildren('transcriptElement') set transcriptElements(elements: QueryList<ElementRef>) {
    if (elements && !this.hasScrolled) {
      const match = elements.find(el => el.nativeElement.id === this.transcriptIndex);
      if (match) {
        match.nativeElement.scrollIntoView();
        this.hasScrolled = true;
      }
    }
  }

  sessionDeviceId: number;
  session: any;
  sessionDevice: any;
  transcripts: any;
  transcriptIndex: string;
  dialogKeywords: any;
  forms = Forms;
  currentForm: Forms = null;
  displayTranscripts: any[];
  subscriptions: any[] = [];
  hasScrolled = false;
  showKeywords = true;
  showDoA = false;

  constructor(private router: Router,
              private route: ActivatedRoute,
              private activeSessionService: ActiveSessionService) {  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.transcriptIndex = params['index'];
    });
    this.route.params.subscribe(params => {
      this.sessionDeviceId = +params['sessionDeviceId'];
      this.activeSessionService.getSession().subscribe( e => {
        this.session = e;
      });
      const deviceSub = this.activeSessionService.getSessionDevice(this.sessionDeviceId).subscribe( e => {
        this.sessionDevice = e;
      });
      const transcriptSub = this.activeSessionService.getSessionDeviceTranscripts(this.sessionDeviceId).subscribe( e => {
        this.transcripts = e;
        this.createDisplayTranscripts();
      });
      this.subscriptions.push(deviceSub, transcriptSub);
    });
  }

  ngOnDestroy() {
    this.subscriptions.map(sub => sub.unsubscribe());
  }

  createDisplayTranscripts() {
    this.displayTranscripts = [];
    for (const transcript of this.transcripts) {
      const result = [];
      const words = transcript.transcript.split(' ');
      for (const word of words) {
        const matchingKeywords = [];
        let highestSimilarity = 0;
        if (this.showKeywords) {
          for (const keyword of transcript.keywords) {
            if (word.toLowerCase().startsWith(keyword.word.toLowerCase())
                && !matchingKeywords.find(item => item.keyword === keyword.keyword)) {
              if (keyword.similarity > highestSimilarity) {
                highestSimilarity = keyword.similarity;
              }
              matchingKeywords.push(keyword);
            }
          }
        }
        result.push({
          'word': word,
          'matchingKeywords': (matchingKeywords.length > 0) ? matchingKeywords : null,
          'color': similarityToRGB(highestSimilarity)
        });
      }
      transcript['words'] = result;
      transcript['doaColor'] = (this.showDoA) ? this.angleToColor(transcript.direction) : this.angleToColor(-1);
      this.displayTranscripts.push(transcript);
    }
  }

  angleToColor(angle: number) {
    if (angle === -1) {
      return 'hsl(0, 100%, 100%)';
    } else {
      return 'hsl(' + angle + ', 100%, 95%)';
    }
  }

  openKeywordDialog(dialogKeywords) {
    this.dialogKeywords = dialogKeywords;
    this.currentForm = this.forms.Keyword;
  }

  openOptionsDialog() {
    this.currentForm = this.forms.Options;
  }

  closeDialog() {
    this.currentForm = null;
  }

  formatSeconds(s) {
    const date = new Date(1000 * Math.floor(s));
    return date.toISOString().substr(11, 8);
  }

  navigateToSession() {
    this.router.navigate(['/sessions/' + this.session.id + '/pods/' + this.sessionDeviceId]);
  }
}
