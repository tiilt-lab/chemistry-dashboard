import { Component, Input } from '@angular/core';
import { SessionService } from '../services/session.service';
import { TranscriptModel } from '../models/transcript';
import { sin, cos } from '../globals';

@Component({
    selector: 'app-heat-map',
    templateUrl: './heat-map.component.html',
    styleUrls: ['./heat-map.component.scss']
})
export class HeatMapComponent {
    _transcripts: TranscriptModel[] = [];
    segments = 8;
    segmentSize: number = 360 / this.segments;
    angleOffset = 0.5;
    radius = 56;
    vectors: any[] = this.calculateVectors();
    showTools = false;
    clipPath: string;
    segmentPath: string;
    showDialog = false;

    @Input('session') session: any;
    @Input('transcripts')
    set setTranscripts(value: any) {
        this._transcripts = value;
        this.calculateDirectionProportions();
    }

    constructor(private sessionService: SessionService) { }

    // Calculate unit vectors that relate to the edges of each segment.
    calculateVectors() {
        const vectors = [];
        let angle = this.angleOffset * this.segmentSize;
        for (let i = 0; i < this.segments + 1; i++) {
            vectors.push([cos(angle), sin(angle)]);
            angle += this.segmentSize;
        }
        return vectors;
    }

    // Associate DoA calcualtions with segments.
    calculateDirectionProportions() {
        const directionCounts = [];
        for (let i = 0; i < this.segments; i++) {
            directionCounts.push(0);
        }

        if (this._transcripts.length > 0) {
            const doaTranscripts = this._transcripts.filter(t => t.direction !== -1);
            const transcriptWeight = 1 / doaTranscripts.length;
            let largestProportion = 0;
            for (const transcript of doaTranscripts) {
                // Adjust the angle.
                let adjustedAngle = transcript.direction + 30.0 - (this.angleOffset * this.segmentSize);
                adjustedAngle = (adjustedAngle + ((adjustedAngle < 0) ? 360 : 0)) % 360;
                // Determine angle segment.
                const segmentIndex = Math.floor(adjustedAngle / this.segmentSize);
                directionCounts[segmentIndex] += transcriptWeight;
                if (directionCounts[segmentIndex] > largestProportion) {
                    largestProportion = directionCounts[segmentIndex];
                }
            }
            if (largestProportion !== 0) {
                const multiplier = 1 / largestProportion;
                for (let i = 0; i < directionCounts.length; i++) {
                    directionCounts[i] = directionCounts[i] * multiplier;
                }
            }
        }

        this.createHeatMap(directionCounts);
        this.createSegmentLines();
    }

    // Draw graph based on segment vectors and segment samples.
    createHeatMap(samples: number[]) {
        let path = '';
        for (let i = 0; i < samples.length; i++) {
            const strength = samples[i] * this.radius;
            path += [(i === 0) ? 'M' : 'L', this.vectors[i][0] * strength + this.radius, this.vectors[i][1] * strength + this.radius,
                    'A', strength, strength, 0, 0, 1,
                    this.vectors[i + 1][0] * strength + this.radius, this.vectors[i + 1][1] * strength + this.radius].join(' ');
        }
        this.clipPath = path;
    }

    createSegmentLines() {
        let path = '';
        for (let i = 0; i < this.vectors.length; i++) {
            const vector = this.vectors[i];
            path += ['M', vector[0] + this.radius, vector[1] + this.radius,
                    'L', vector[0] * this.radius + this.radius, vector[1] * this.radius + this.radius].join(' ');
        }
        this.segmentPath = path;
    }

    segmentChange(e: any) {
        this.segmentSize = 360 / this.segments;
        this.vectors = this.calculateVectors();
        this.calculateDirectionProportions();
    }

    offsetChange(e: any) {
        this.vectors = this.calculateVectors();
        this.calculateDirectionProportions();
    }

    resetDiagram() {
        this.segments = 8;
        this.segmentSize = 360 / this.segments;
        this.angleOffset = 0.5;
        this.vectors = this.calculateVectors();
        this.calculateDirectionProportions();
    }

    toggleDisplay(show: boolean) {
        this.showDialog = show;
    }
}
