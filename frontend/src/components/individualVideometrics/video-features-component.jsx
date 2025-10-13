import { useEffect, useState } from "react";
import { IndividualVideoMetricPage } from "./html-pages-video-individual";

function AppIndividualVideoFeaturesComponent(props) {
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

  
  useEffect(() => {
    updateGraphs();
  });

  //update new metrics (individual)
  const updateGraphs = () => {
    const valueArrays = [
      { name: "Facial Emotions", values: [],time:[] },
      { name: "Attention Level", values: [],time:[] },
      { name:"Object Focused On", values: [], time:[]}
      
    ];
    if(!props.videometrics || !props.videometrics.length)
    {
      setFeatures(valueArrays);
      return;
    }
    
    //filter speaker metrics from video metrics based on the spkrId
    // const speaker_video_metric = props.videometrics.filter(v => v.student_username === props.spkrId)
    
    
    props.videometrics.forEach((v) => {
      
      //accumulate each score into their value array
      valueArrays[0].values.push(v.facial_emotion);
      valueArrays[1].values.push(v.attention_level);
      valueArrays[2].values.push(v.object_on_focus);

      valueArrays[0].time.push(v.time_stamp);
      valueArrays[1].time.push(v.time_stamp);
      valueArrays[2].time.push(v.time_stamp);
    });
    // console.log("i returned ", props.spkrId)
    // console.log("video mtric data: ", valueArrays)
    
    // //smooth the values of the value array over 10 values
    // for (const valueArray of valueArrays) {
    //   const length = valueArray.values.length;
    //   const average =
    //     valueArray.values.reduce((sum, current) => sum + current, 0) /
    //     (length > 0 ? length : 1);
    //   const last = length > 0 ? valueArray.values[length - 1] : 0;
    //   const trend = last > average ? 1 : last === average ? 0 : -1;
    //   let path = "";
    //   const smoothedValues = [];

    //   // Calculate the average of each 10 x units
    //   for (let i = 0; i < length; i += 10) {
    //     const chunk = valueArray.values.slice(i, i + 10);
    //     const chunkAverage =
    //       chunk.reduce((sum, current) => sum + current, 0) / chunk.length;
    //     smoothedValues.push(chunkAverage);
    //   }

    //   // Generate the SVG path using the smoothed values
    //   for (let i = 0; i < smoothedValues.length; i++) {
    //     const xPos = Math.round(((i + 1) / smoothedValues.length) * svgWidth);
    //     const yPos =
    //       svgHeight - Math.round((smoothedValues[i] / 100) * svgHeight);
    //     path += i === 0 ? "M" : "L";
    //     path += `${xPos} ${yPos} `;
    //   }

    //   valueArray["average"] = average;
    //   valueArray["last"] = last;
    //   valueArray["trend"] = trend;
    //   valueArray["path"] = path;
    // }
    setFeatures(valueArrays);
  };

  const getInfo = (featureName) => {
    switch (featureName) {
      case "Facial Emotions":
        {
          setFeatureDescription("Your  facial emotional expressions during the collaboration activity. Very important measure of group dynamics");
          break;
        }
      case "Attention Level":
        {
          setFeatureDescription("Your attention level based on your focus during the collaboration activity. Very important to guague you partiipation");
          break;
        }
      case "Object_Focused_on":
        {
          setFeatureDescription("The Objects within the collaboration environment you were most focused on. Very important for identifying distractions");
          break;
        }
      default:
        console.log("no text");
    }
    setFeatureHeader(featureName);
    setShowFeatureDialog(true);
  };

  const closeDialog = () => {
    setShowFeatureDialog(false);
  };

  return (
    <IndividualVideoMetricPage
      featureHeader={featureHeader}
      featureDescription={featureDescription}
      closeDialog={closeDialog}
      showFeatureDialog={showFeatureDialog}
      features={features}
      getInfo={getInfo}
      showFeatures={props.showFeatures}
    />
  );
}

export { AppIndividualVideoFeaturesComponent };
