import { useEffect, useState } from 'react';
import { SessionModel } from '../models/session';
import { TranscriptModel } from '../models/transcript';
import {FeaturePage} from './html-pages'

function AppIndividualFeaturesComponent(props) {
  // @Input('session') session: SessionModel;
  
  // @Input('transcripts')
  // set setTranscripts(value: any) {
  //   this._transcripts = value;
  //   this.updateGraphs();
  // }
  const svgWidth = 74;
  const svgHeight = 39;
  //const [_transcripts, setTranscript] = useState([]);
  const [features, setFeatures] = useState([]);
  const [featureDescription, setFeatureDescription] = useState(null);
  const [featureHeader, setFeatureHeader] = useState(null);
  const [showFeatureDialog, setShowFeatureDialog] = useState(false);
  const [trigger, setTrigger] = useState(0);

  useEffect(()=>{
    updateGraphs()
  },[props.transcripts])
  
  
  useEffect(()=>{
    if (trigger > 0) {
      console.log("reloaded page");
    }
  },[trigger])
  
  //update new metrics (individual)
  const updateGraphs = () => {
    const valueArrays = [
      { 'name': 'Participation', 'values': [] },
      { 'name': 'Social Impact', 'values': [] },
      { 'name': 'Responsivity', 'values': [] },
      { 'name': 'Internal Cohesion', 'values': [] },
      { 'name': 'Newness', 'values': [] },
      { 'name': 'Communication Density', 'values': [] }
    ];
  
    props.transcripts.map(t => {
      valueArrays[5].values.push(t.participation_value);
      valueArrays[6].values.push(t.social_impact_value);
      valueArrays[7].values.push(t.responsivity_value);
      valueArrays[8].values.push(t.internal_cohesion_value);
      valueArrays[9].values.push(t.newness_value);
      valueArrays[10].values.push(t.communication_density_value);
    });
  
    for (const valueArray of valueArrays) {
      const length = valueArray.values.length;
      const average = valueArray.values.reduce((sum, current) => sum + current, 0) / ((length > 0) ? length : 1);
      const last = (length > 0) ? valueArray.values[length - 1] : 0;
      const trend = (last > average) ? 1 : (last === average) ? 0 : -1;
      let path = '';
      const smoothedValues = [];
  
      // Calculate the average of each 10 x units
      for (let i = 0; i < length; i += 10) {
        const chunk = valueArray.values.slice(i, i + 10);
        const chunkAverage = chunk.reduce((sum, current) => sum + current, 0) / chunk.length;
        smoothedValues.push(chunkAverage);
      }
  
      // Generate the SVG path using the smoothed values
      for (let i = 0; i < smoothedValues.length; i++) {
        const xPos = Math.round(((i + 1) / smoothedValues.length) * svgWidth);
        const yPos = svgHeight - Math.round((smoothedValues[i] / 100) * svgHeight);
        path += (i === 0) ? 'M' : 'L';
        path += `${xPos} ${yPos} `;
      }
  
      valueArray['average'] = average;
      valueArray['last'] = last;
      valueArray['trend'] = trend;
      valueArray['path'] = path;
    }
    setFeatures(valueArrays);
  }

  const getInfo = (featureName) =>{
    switch (featureName) {
      case 'Participation': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
      case 'Social mpact': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
      case 'Responsivity': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
      case 'Internal Cohesion': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
      case 'Newness': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
      case 'Communication Density': {
        setFeatureDescription('Placeholder texts.');
      }
      break;
    }
    setFeatureHeader(featureName);
    setShowFeatureDialog(true);
  }

  const closeDialog = ()=> {
    setShowFeatureDialog(false);
  }

  return(
    <FeaturePage
    featureHeader = {featureHeader}
    featureDescription = {featureDescription}
    closeDialog = {closeDialog}
    showFeatureDialog = {showFeatureDialog}
    features = {features}
    getInfo = {getInfo}
    showFeatures = {props.showFeatures}
    />
  )
}

export {AppIndividualFeaturesComponent}
