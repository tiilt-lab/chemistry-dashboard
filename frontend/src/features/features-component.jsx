import { useEffect, useState } from 'react';
import { SessionModel } from '../models/session';
import { TranscriptModel } from '../models/transcript';
import {FeaturePage} from './html-pages'

function AppFeaturesComponent(props) {
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
  
  const updateGraphs = ()=> {
    //////attempt to change this into d3 radar chart before making a folder for this
    //general format of my data (time-independent)
    /*let radfeatures = [];
    let raddata = props.transcripts;
    let analytical_sum = 0;
    let authenticity_sum = 0;
    let certainty_sum = 0;
    let clout_sum = 0;
    let emotional_sum = 0;
    for (const i in raddata) {
      analytical_sum += parseInt(raddata[i].analytic_thinking_value);
      authenticity_sum += parseInt(raddata[i].authenticity_value);
      certainty_sum += parseInt(raddata[i].certainty_value);
      clout_sum += parseInt(raddata[i].clout_value);
      emotional_sum += parseInt(raddata[i].emotional_tone_value);
    }
    let total_sum = analytical_sum+authenticity_sum+
    certainty_sum+clout_sum+emotional_sum;
    radfeatures.push({"axis": "Analytical", "value": Math.round(100*analytical_sum/total_sum)/100});
    radfeatures.push({"axis": "Authenticity", "value": Math.round(100*authenticity_sum/total_sum)/100});
    radfeatures.push({"axis": "Certainty", "value": Math.round(100*certainty_sum/total_sum)/100});
    radfeatures.push({"axis": "Clout", "value": Math.round(100*clout_sum/total_sum)/100});
    radfeatures.push({"axis": "Emotional", "value": Math.round(100*emotional_sum/total_sum)/100});
    //console.log([radfeatures]);*/
    
    // Create feature array.
    const valueArrays = [{ 'name': 'Emotional tone', 'values': [] },
                        { 'name': 'Analytic thinking', 'values': [] },
                        { 'name': 'Clout', 'values': [] },
                        { 'name': 'Authenticity', 'values': [] },
                        { 'name': 'Confusion', 'values': [] }];
      props.transcripts.map(t => {
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
        const xPos = Math.round(((i + 1) / length) * svgWidth);
        const yPos = svgHeight - Math.round((valueArray.values[i] / 100) * svgHeight);
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
      case 'Emotional tone': {
        setFeatureDescription('Scores above 50 indicate a positive emotional tone. Scores below 50 indicate a negative emotional tone.');
      }
      break;
      case 'Analytic thinking': {
        setFeatureDescription('Scores above 50 indicate analytic thinking. Scores below 50 indicate narrative thinking.');
      }
      break;
      case 'Clout': {
        setFeatureDescription('Scores above 50 indicate higher levels of confidence or leadership.');
      }
      break;
      case 'Authenticity': {
        setFeatureDescription('Scores above 50 indicate higher levels of honesty or authentic communication.');
      }
      break;
      case 'Confusion': {
        setFeatureDescription('Scores above 50 indicate higher levels of confusion in a speaker’s communication.');
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

export {AppFeaturesComponent}
