import { useEffect, useState } from "react";
import { IndividualFeaturePage } from "./html-pages-individual";

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

  useEffect(() => {
    updateGraphs();
  }, [props.transcripts, props.spkrId]);

  //update new metrics (individual)
  const updateGraphs = () => {
    const valueArrays = [
      { name: "Participation", values: [] },
      { name: "Social Impact", values: [] },
      { name: "Responsivity", values: [] },
      { name: "Internal Cohesion", values: [] },
      { name: "Newness", values: [] },
      { name: "Communication Density", values: [] },
    ];
    if(!props.transcripts || !props.transcripts.length || props.spkrId === -1)
    {
      setFeatures(valueArrays);
      return;
    }
    props.transcripts.forEach((t) => {
      //select speaker metrics from transcripts based on the spkrId
      const speaker_metric = t.speaker_metrics.find(
        (item) => item.speaker_id === props.spkrId
      );

      //accumulate each score into their value array
      valueArrays[0].values.push(speaker_metric.participation_score * 100);
      valueArrays[1].values.push(speaker_metric.social_impact * 100);
      valueArrays[2].values.push(speaker_metric.responsivity * 100);
      valueArrays[3].values.push(speaker_metric.internal_cohesion * 100);
      valueArrays[4].values.push(speaker_metric.newness * 100);
      valueArrays[5].values.push(speaker_metric.communication_density * 100);
    });

    //smooth the values of the value array over 10 values
    for (const valueArray of valueArrays) {
      const length = valueArray.values.length;
      const average =
        valueArray.values.reduce((sum, current) => sum + current, 0) /
        (length > 0 ? length : 1);
      const last = length > 0 ? valueArray.values[length - 1] : 0;
      const trend = last > average ? 1 : last === average ? 0 : -1;
      let path = "";
      const smoothedValues = [];

      // Calculate the average of each 10 x units
      for (let i = 0; i < length; i += 10) {
        const chunk = valueArray.values.slice(i, i + 10);
        const chunkAverage =
          chunk.reduce((sum, current) => sum + current, 0) / chunk.length;
        smoothedValues.push(chunkAverage);
      }

      // Generate the SVG path using the smoothed values
      for (let i = 0; i < smoothedValues.length; i++) {
        const xPos = Math.round(((i + 1) / smoothedValues.length) * svgWidth);
        const yPos =
          svgHeight - Math.round((smoothedValues[i] / 100) * svgHeight);
        path += i === 0 ? "M" : "L";
        path += `${xPos} ${yPos} `;
      }

      valueArray["average"] = average === NaN ? 0 : average;
      valueArray["last"] = last;
      valueArray["trend"] = trend;
      valueArray["path"] = path;
    }
    setFeatures(valueArrays);
  };

  const getInfo = (featureName) => {
    switch (featureName) {
      case "Participation":
        {
          setFeatureDescription("How much you participate above or below the average.");
          break;
        }
      case "Social mpact":
        {
          setFeatureDescription("How much your speech is related to the following response.");
          break;
        }
      case "Responsivity":
        {
          setFeatureDescription("How much your response is related to the other's speech.");
          break;
        }
      case "Internal Cohesion":
        {
          setFeatureDescription("How much your speech is realted to itself.");
          break;
        }
      case "Newness":
        {
          setFeatureDescription("How much new info you present throughout the discussion");
          break;
        }
      case "Communication Density":
        {
          setFeatureDescription("The amount of word per speech segment");
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
    <IndividualFeaturePage
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

export { AppIndividualFeaturesComponent };
