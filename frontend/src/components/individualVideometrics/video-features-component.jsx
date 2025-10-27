import { useEffect, useState } from "react";
import { IndividualVideoMetricPage } from "./html-pages-video-individual";
import { Line } from "react-chartjs-2";
import {
  Chart,
  LineElement,
  PointElement,
  LinearScale,   // x scale (time as numbers/seconds)
  CategoryScale, // y scale (categories)
  Tooltip,
  Legend,
  Title,
} from "chart.js";

Chart.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend, Title);

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
  const [facialEmotionDataset, setFacialEmotionDataset] = useState([]);
  const [objectFocusedDataset, setObjectFocusedDataset] = useState([]);
  const [attentionLevelDataset, setAttentionLevelDataset] = useState({});
  const [featureDescription, setFeatureDescription] = useState(null);
  const [featureHeader, setFeatureHeader] = useState(null);
  const [showFeatureDialog, setShowFeatureDialog] = useState(false);


  useEffect(() => {
      updateGraphs();
  });


  //update new metrics (individual)
  const updateGraphs = () => {
    const valueArrays = [
      { name: "Facial Emotions", values: [], time: [] },
      { name: "Attention Level", values: [], time: [] },
      { name: "Object Focused On", values: [], time: [] }

    ];
    const facial_emotion_data = []
    const object_focused_data = []
    if (props.videometrics.length <= 0) {
      console.log("no videometrics or speaker id")
      setFeatures(valueArrays);
      return;
    }

    //filter speaker metrics from video metrics based on the spkrId
    // const speaker_video_metric = props.videometrics.filter(v => v.student_username === props.spkrId)


    props.videometrics.forEach((v) => {

      //accumulate each score into their value array
      valueArrays[0].values.push(v.facial_emotion);
      valueArrays[0].time.push(v.time_stamp);
      valueArrays[1].values.push(v.attention_level);
      valueArrays[1].time.push(v.time_stamp);
      valueArrays[2].values.push(v.object_on_focus);
      valueArrays[2].time.push(v.time_stamp);


      facial_emotion_data.push({ time: v.time_stamp, category: v.facial_emotion })
      object_focused_data.push({ time: v.time_stamp, category: v.object_on_focus })

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
    setFacialEmotionDataset(facial_emotion_data)
    setObjectFocusedDataset(object_focused_data)
    setAttentionLevelDataset({ values: valueArrays[1].values, time: valueArrays[1].time })
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

  const emotionTimelineCategorical = (feature, height = 320, width = 640) => {
    // Build (x,y) objects directly; y is categorical (emotion string)
    const points = feature.time.map((t, i) => ({ x: t, y: feature.values[i] }));

    // Optional: fix the category order so the y-axis doesn’t reorder dynamically
    const emotionOrder = ["angry", "disgust", "fear", "happy", "neutral", "surprise", "sad"];

    const data = {
      datasets: [
        {
          label: feature.name,
          data: points,          // [{x: 0.0, y: "neutral"}, ...]
          parsing: false,        // tell Chart.js we’re giving explicit {x,y}
          stepped: true,         // step timeline look
          borderWidth: 2,
          pointRadius: 0,
        },
      ],
    };

    const options = {
      responsive: false,        // we’ll control canvas size via props
      plugins: {
        legend: { display: false },
        title: { display: true, text: "Emotion Over Time (Categorical Y)" },
        tooltip: {
          callbacks: {
            // Show clean tooltip like: Time: 1.2s — Emotion: happy
            label: (ctx) => `Emotion: ${ctx.parsed.y}`,
            title: (items) =>
              items?.length ? `Time: ${items[0].parsed.x}s` : "",
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          title: { display: true, text: "Time (s)" },
          ticks: { autoSkip: false },
          grid: { drawOnChartArea: true },
        },
        y: {
          type: "category",
          // If you want to lock order, set labels explicitly; otherwise Chart.js uses the data’s order
          labels: emotionOrder,
          title: { display: true, text: feature.name },
          ticks: { autoSkip: false }, // show every emotion row
          grid: { drawOnChartArea: true },
        },
      },
    }

    return (
      <div>
        <Line data={data} options={options} height={height} width={width} />
      </div>
    );
  }

  return (
    <IndividualVideoMetricPage
      featureHeader={featureHeader}
      featureDescription={featureDescription}
      closeDialog={closeDialog}
      showFeatureDialog={showFeatureDialog}
      features={features}
      facialEmotionDataset={facialEmotionDataset}
      objectFocusedDataset={objectFocusedDataset}
      attentionLevelDataset={attentionLevelDataset}
      getInfo={getInfo}
      showFeatures={props.showFeatures}
      emotionTimelineCategorical={emotionTimelineCategorical}
    />
  );
}

export { AppIndividualVideoFeaturesComponent };
