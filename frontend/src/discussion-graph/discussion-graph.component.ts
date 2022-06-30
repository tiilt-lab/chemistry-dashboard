import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActiveSessionService } from '../services/active-session.service';
import { Router } from '@angular/router';
import { similarityToRGB, formatSeconds } from '../globals';

enum Forms {
  keywords = 1,
  devices,
  stats
}

@Component({
  selector: 'app-discussion-graph',
  templateUrl: './discussion-graph.component.html',
  styleUrls: ['./discussion-graph.component.scss']
})
export class DiscussionGraphComponent implements OnInit, OnDestroy {

  // Server data
  session: any;
  transcripts: any[] = [];
  sessionDevices: any[] = [];
  contributions: number;
  speakingTime: number;
  showQuestions = false;
  showGraph = false;
  cumulativePercent = 0;
  subscriptions = [];
  currentForm: Forms;
  forms = Forms;

  displayKeywords: any;
  displayQuestions: any[] = [];
  displayDevices: any = [];
  timestamps: string[] = [];
  selectedDevice: any;
  selectedPercent: number;

  constructor(private router: Router,
              private activeSessionService: ActiveSessionService) { }

  ngOnInit() {
    const deviceSub = this.activeSessionService.getSessionDevices().subscribe(e => {
      this.sessionDevices = e;
      this.sessionDevices.map(sd => {
        sd['visible'] = true;
        sd['transcripts'] = [];
      });
      this.updateGraph();
    });

    const sessionTranscripts = this.activeSessionService.getTranscripts().subscribe(e => {
      this.transcripts = e;
      this.updateGraph();
    });

    const sessionModel = this.activeSessionService.getSession().subscribe(e => {
      this.session = e;
    });
    this.subscriptions.push(deviceSub, sessionTranscripts, sessionModel);
  }

  ngOnDestroy() {
    this.subscriptions.map(sub => sub.unsubscribe());
  }

  openForms(form: Forms, data: any = null) {
    this.currentForm = form;
    if (this.currentForm === Forms.stats) {
      this.selectedDevice = data;
      let totalTime = 0;
      const contributionsArray = this.transcripts.filter(transcript => transcript.session_device_id === this.selectedDevice.id);
      this.contributions = (contributionsArray.length);
      for (let i = 0; i < contributionsArray.length; i++) {
        const transcript = contributionsArray[i];
        totalTime += transcript.length;
      }
      this.speakingTime = totalTime;
      this.displayQuestions = this.parseQuestions(this.selectedDevice);
    } else if (this.currentForm === Forms.keywords) {
      this.displayKeywords = data;
    }
  }

  closeForm() {
    this.currentForm = null;
    this.showQuestions = false;
    this.showGraph = false;
  }

  updateGraph() {
    if (this.transcripts.length > 0 && this.sessionDevices.length > 0) {
      this.displayDevices = [];
      for (const device of this.sessionDevices) {
        if (device['visible']) {
          this.displayDevices.push(device); // This will not work if user has deactivated some devices!!
        }
      }
      for (const transcript of this.transcripts) {
        const matchingDevice = this.displayDevices.find(d => d.id === transcript.session_device_id);
        if (matchingDevice != null) {
          matchingDevice['transcripts'].push(this.createDisplayTranscript(transcript));
        }
      }
      this.generateTimestamps();
    }
  }

  navigateToSession() {
    this.router.navigate(['/sessions/' + this.session.id]);
  }

  generateTimestamps() {
    this.timestamps = ['00:00'];
    const lastTranscript = this.transcripts[this.transcripts.length - 1];
    const totalSeconds = (lastTranscript.start_time + lastTranscript.length);
    const stepSize = 5;
    for (let i = stepSize; i < totalSeconds; i += stepSize) {
      this.timestamps.push(formatSeconds(i));
    }
  }

  parseQuestions(session_device) {
    const contributionsArray = this.transcripts.filter(transcript => transcript.session_device_id === session_device.id);
    const questionTranscripts = contributionsArray.filter(transcript => transcript.question);

    const questions = [];
    for (const transcript of questionTranscripts) {
      const sentences = transcript.transcript.match( /[^\.!\?]+[\.!\?]+/g );
      for (const sentence of sentences) {
        if (sentence.includes('?')) {
          questions.push(sentence);
        }
      }
    }
    return questions;
  }

  createDisplayTranscript(transcript, highlight = false) {
    const sentences = transcript.transcript.match( /([^\.!\?]+[\.!\?]+)|([^\.!\?]+$)/g );
    const words = [];
    for (const sentence of sentences) {
      sentence.split(' ').map(word => words.push({'word': word, 'highlight': sentence.includes('?') && highlight }));
    }
    for (const word of words) {
      const matchingKeywords = [];
      let highestSimilarity = 0;
      for (const keyword of transcript.keywords) {
        if (word.word.toLowerCase().startsWith(keyword.word.toLowerCase())
        && !matchingKeywords.find(item => item.keyword === keyword.keyword)) {
          if (keyword.similarity > highestSimilarity) {
            highestSimilarity = keyword.similarity;
          }
          matchingKeywords.push(keyword);
        }
      }
      word['matchingKeywords'] = (matchingKeywords.length > 0) ? matchingKeywords : null;
      word['color'] = similarityToRGB(highestSimilarity);
    }
    return {
      'transcript_id': transcript.id,
      'speaker_tag': transcript.speaker_tag,
      'question': transcript.question,
      'highlight': highlight,
      'start_time': transcript.start_time,
      'transcript': words,
      'device_id': transcript.session_device_id,
      'length': transcript.length,
    };
  }

  toggleGraph(open: boolean, device = null) {
    this.showGraph = open;
    if (this.showGraph) {
      const huedelta = Math.trunc(360 / this.displayDevices.length);
      const percent = this.getSpeakingPercent(device);
      const roundedPercent = Math.floor(percent * 100);
      this.selectedPercent = roundedPercent;
      for (let i = 0; i < this.displayDevices.length; i++) {
        this.displayDevices[i]['path'] = this.setPiePieceProperties(this.displayDevices[i]);
        if (this.displayDevices[i] === device) {
          this.displayDevices[i]['selected'] = true;
          this.displayDevices[i]['color'] = `hsl(${i * huedelta},100%,80%)`;
        } else {
          this.displayDevices[i]['selected'] = false;
          this.displayDevices[i]['color'] = `hsl(${i * huedelta},100%,90%)`;
        }
      }
    }
  }

  toggleQuestions() {
    this.showQuestions = !this.showQuestions;
  }

  getSpeakingPercent(device) {
    this.showGraph = true;
    let totalTime = 0;
    const deviceContribution = this.transcripts.filter(transcript => transcript.session_device_id === device.id);
    for (let i = 0; i < deviceContribution.length; i++) {
      const transcript = deviceContribution[i];
      totalTime += transcript.length;
    }
    const rawPercent = totalTime / this.getTotalSpeakingTime();
    return rawPercent;
  }

  getTotalSpeakingTime() {
    let allDeviceContributions = 0;
    const validTranscripts = [];
    for (const dev of this.displayDevices) {
      const deviceTranscripts = this.transcripts.filter(transcript => transcript.session_device_id === dev.id);
      for (const trans of deviceTranscripts) {
        validTranscripts.push(trans);
      }
    }
    for (const transcript of validTranscripts) {
      allDeviceContributions += transcript.length;
    }
    return allDeviceContributions;
  }

  getDisplayPercent(device) {
    const percent = this.getSpeakingPercent(device);
    const roundedPercent = Math.floor(percent * 100);
    this.selectedPercent = roundedPercent;
    return roundedPercent;
  }

  setPiePieceProperties(device) {
    const slice = {percent: this.getSpeakingPercent(device)};
    const [startX, startY] = this.getCoordinatesForPercent(this.cumulativePercent);
    this.cumulativePercent += slice.percent;
    const [endX, endY] = this.getCoordinatesForPercent(this.cumulativePercent);
    const largeArcFlag = slice.percent > .5 ? 1 : 0;

    const pathData = [
      `M ${startX} ${startY}`,
      `A 1 1 0 ${largeArcFlag} 1 ${endX} ${endY}`,
      `L 0 0`
    ].join(' ');
    return pathData;
  }

  getCoordinatesForPercent(percent) {
    const x = Math.cos(2 * Math.PI * percent);
    const y = Math.sin(2 * Math.PI * percent);
    return [x, y];
  }

  highlightQuestions(transcript) {
    transcript['highlight'] = !transcript['highlight'];
    const foundTranscript = this.transcripts.find(t => t.id === transcript.transcript_id);
    const newTranscript = this.createDisplayTranscript(foundTranscript, transcript['highlight']);
    Object.assign(transcript, newTranscript);
  }
}
