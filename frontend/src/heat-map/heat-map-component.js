import { SessionService } from '../services/session-service';
import { TranscriptModel } from '../models/transcript';
import { sin, cos } from '../globals';
import { useEffect, useState } from 'react';
import {HeatMapPage} from './html-pages'


function  AppHeatMapComponent(props) {
    
    const [segmentSize, setSegmentSize] = useState(360 / 8);
    const [radius, setRadius] = useState(56);
    const [angleOffset, setAngleOffset] = useState(0.5);
    const [segments, setSegments] = useState(8); 
    const [_transcripts, setTranscripts] = useState(props.transcripts);
    const [vectors, setVectors] = useState([]);
    const [showTools, setShowTools] = useState(false);
    const [clipPath, setClipPath] = useState("");
    const [segmentPath, setSegmentPath] = useState("");
    const [showDialog, setShowDialog] = useState(false);
    const [callbackfunc, setCallbackFunc] = useState();
    const [reload, setReload] = useState(false)

    useEffect(()=>{
        if(vectors.length === 0){
        setVectors(calculateVectors())
        }
        calculateDirectionProportions();
        setReload(true)
    },[reload])
    // @Input('session') session: any;
    // @Input('transcripts')
    // set setTranscripts(value: any) {
    //     this._transcripts = value;
    //     this.calculateDirectionProportions();
    // }


    // Calculate unit vectors that relate to the edges of each segment.
    const calculateVectors = () =>{
        const vectors = [];
        let angle = angleOffset * segmentSize;
        for (let i = 0; i < segments + 1; i++) {
            vectors.push([cos(angle), sin(angle)]);
            angle += segmentSize;
        }
        return vectors;
    }

    // Associate DoA calcualtions with segments.
    const calculateDirectionProportions = ()=> {
        const directionCounts = [];
        for (let i = 0; i < segments; i++) {
            directionCounts.push(0);
        }
        
        if (_transcripts.length > 0) {
            const doaTranscripts = _transcripts.filter(t => t.direction !== -1);
            const transcriptWeight = 1 / doaTranscripts.length;
            let largestProportion = 0;
            for (const transcript of doaTranscripts) {
                // Adjust the angle.
                let adjustedAngle = transcript.direction + 30.0 - (angleOffset * segmentSize);
                adjustedAngle = (adjustedAngle + ((adjustedAngle < 0) ? 360 : 0)) % 360;
                // Determine angle segment.
                const segmentIndex = Math.floor(adjustedAngle / segmentSize);
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

        createHeatMap(directionCounts);
        createSegmentLines();
    }

    // Draw graph based on segment vectors and segment samples.
    const createHeatMap = (samples)=> {
        let path = '';
        if (vectors.length > 0) {
        for (let i = 0; i < samples.length; i++) {
            const strength = samples[i] * radius;
            path += [(i === 0) ? 'M' : 'L', vectors[i][0] * strength + radius, vectors[i][1] * strength + radius,
                    'A', strength, strength, 0, 0, 1,
                    vectors[i + 1][0] * strength + radius, vectors[i + 1][1] * strength + radius].join(' ');
        }
    }
        setClipPath(path);
    }

    const createSegmentLines = ()=> {
        let path = '';
        for (let i = 0; i < vectors.length; i++) {
            const vector = vectors[i];
            path += ['M', vector[0] + radius, vector[1] + radius,
                    'L', vector[0] * radius + radius, vector[1] * radius + radius].join(' ');
        }
        setSegmentPath(path);
    }

   const segmentChange = (e)=> {
        const seg = e.target.value;
        setSegments(seg)
        setSegmentSize(360 / seg);
        setVectors(calculateVectors());
        calculateDirectionProportions();
    }

    const offsetChange = (e)=>{
        const angle = e.target.value
        setAngleOffset(angle)
        setVectors(calculateVectors());
        calculateDirectionProportions();
    }

    const resetDiagram = ()=> {
        setSegments(8);
        setSegmentSize(360 /segments);
        setAngleOffset(0.5);
        setVectors(calculateVectors());
        calculateDirectionProportions();
    }

    const toggleDisplay = (show)=> {
        setShowDialog(show);
    }

    return(
        <HeatMapPage 
            showTools = {showTools}
            clipPath = {clipPath}
            segmentPath = {segmentPath}
            setShowTools = {setShowTools}
            segmentChange = {segmentChange}
            offsetChange = {offsetChange}
            toggleDisplay = {toggleDisplay}
            callbackfunc = {callbackfunc}
            setCallbackFunc = {setCallbackFunc}
            resetDiagram = {resetDiagram}
            showDialog = {showDialog}
            segments = {segments}
            angleOffset = {angleOffset}
        />
    )
}

export {AppHeatMapComponent}
