import * as d3 from "d3";
import { useEffect, useState } from 'react';
import {RadarPage} from './html-pages';

function AppRadarComponent(props) {
  //list of elements to put in html pages (instead of this)
  const [features, setFeatures] = useState([]);
  const [maxValue, setMaxValue] = useState(0);
  const [valSum, setValSum] = useState(0);
  
  useEffect(()=>{
    updateGraphs()
  },[props.transcripts, props.radarTrigger])
  
  const updateGraphs = () => {
    //general format of data (trying to make time-dependent)
    let radfeatures = [];
    let raddata = props.transcripts;
    let analytical_sum = 0;
    let authenticity_sum = 0;
    let certainty_sum = 0;
    let clout_sum = 0;
    let emotional_sum = 0;
    for (const i in raddata) {
      if (props.start <= raddata[i].start_time && raddata[i].start_time <= props.end) {
        analytical_sum += parseInt(raddata[i].analytic_thinking_value);
        authenticity_sum += parseInt(raddata[i].authenticity_value);
        certainty_sum += parseInt(raddata[i].certainty_value);
        clout_sum += parseInt(raddata[i].clout_value);
        emotional_sum += parseInt(raddata[i].emotional_tone_value);
      }
    }
    let total_sum = analytical_sum+authenticity_sum+
    certainty_sum+clout_sum+emotional_sum;
    radfeatures.push({"axis": "Emotional", "value": Math.round(100*emotional_sum/total_sum)/100});
    radfeatures.push({"axis": "Analytical", "value": Math.round(100*analytical_sum/total_sum)/100});
    radfeatures.push({"axis": "Clout", "value": Math.round(100*clout_sum/total_sum)/100});
    radfeatures.push({"axis": "Authenticity", "value": Math.round(100*authenticity_sum/total_sum)/100});
    radfeatures.push({"axis": "Certainty", "value": Math.round(100*certainty_sum/total_sum)/100});
    //things to set
    setValSum(total_sum);
    setFeatures(radfeatures);
    setMaxValue(d3.max(require("underscore").flatten([radfeatures]).map(d => d.value)));
  }
  
  return(
    <RadarPage
    features = {features}
    maxValue = {maxValue}
    valSum = {valSum}
    showFeatures = {props.showFeatures}
    />
  )

}

export {AppRadarComponent}
