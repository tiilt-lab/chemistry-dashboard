import { Component, Input } from '@angular/core';
import { SessionModel } from '../models/session';
import { TranscriptModel } from '../models/transcript';

@Component({
  selector: 'app-pie-chart',
  templateUrl: './pie-chart.component.html',
  styleUrls: ['./pie-chart.component.scss']
})
export class PieChartComponent {
  @Input('session') session: SessionModel;
  @Input('transcripts')
  set setTranscripts(value: any) {
    this._transcripts = value;
    this.updateGraphs();
  }
  private _transcripts: TranscriptModel[] = [];
  private svgWidth = 74;
  private svgHeight = 39;
  features: any[] = [];
  featureDescription = null;
  featureHeader = null;
  showFeatureDialog = false;

  constructor() { }

  updateGraphs() {
    // Create feature array.
    const valueArrays = [{ 'name': 'Emotional tone', 'values': [] },
                        { 'name': 'Analytic thinking', 'values': [] },
                        { 'name': 'Clout', 'values': [] },
                        { 'name': 'Authenticity', 'values': [] },
                        { 'name': 'Confusion', 'values': [] }];
    this._transcripts.map(t => {
      valueArrays[0].values.push(t.emotional_tone_value);
      valueArrays[1].values.push(t.analytic_thinking_value);
      valueArrays[2].values.push(t.clout_value);
      valueArrays[3].values.push(t.authenticity_value);
      valueArrays[4].values.push(t.certainty_value);
    });
    for (const valueArray of valueArrays) {
      const length = valueArray.values.length;
      const average = valueArray.values.reduce((sum, current) => sum + current, 0) / ((length > 0) ? length : 1);
      const last = (length > 0) ? valueArray.values[length - 1] : 0;
      const trend = (last > average) ? 1 : (last === average) ? 0 : -1;
 
      let path = '';
      for (let i = 0; i < length; i++) {
        const xPos = Math.round(((i + 1) / length) * this.svgWidth);
        const yPos = this.svgHeight - Math.round((valueArray.values[i] / 100) * this.svgHeight);
        path += (i === 0) ? 'M' : 'L';
        path += `${xPos} ${yPos} `;
      }
      valueArray['average'] = average;
      valueArray['last'] = last;
      valueArray['trend'] = trend;
      valueArray['path'] = path;
    }
    this.features = valueArrays;
  }

  getInfo(featureName) {
    switch (featureName) {
      case 'Emotional tone': {
        this.featureDescription = 'Scores above 50 indicate a positive emotional tone. Scores below 50 indicate a negative emotional tone.';
      }
      break;
      case 'Analytic thinking': {
        this.featureDescription = 'Scores above 50 indicate analytic thinking. Scores below 50 indicate narrative thinking.';
      }
      break;
      case 'Clout': {
        this.featureDescription = 'Scores above 50 indicate higher levels of confidence or leadership.';
      }
      break;
      case 'Authenticity': {
        this.featureDescription = 'Scores above 50 indicate higher levels of honesty or authentic communication.';
      }
      break;
      case 'Confusion': {
        this.featureDescription = 'Scores above 50 indicate higher levels of confusion in a speaker’s communication.';
      }
      break;
    }
    this.featureHeader = featureName;
    this.showFeatureDialog = true;
  }

  closeDialog() {
    this.showFeatureDialog = false;
  }
}

