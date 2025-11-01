import { useCallback, useEffect, useState } from "react";
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
  //  console.log("session1 video metrics AppIndividualVideoFeaturesComponent");
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


  // useEffect(() => {
  //   // console.log("updating video metrics component", props.videometrics);
  //     updateGraphs();
  // },[]);


  //update new metrics (individual)
  const updateGraphs = useCallback((videometrics) => {
    const valueArrays = [
      { name: "Facial Emotions", values: [], time: [] },
      { name: "Attention Level", values: [], time: [] },
      { name: "Object Focused On", values: [], time: [] }

    ];
    const facial_emotion_data = []
    const object_focused_data = []
    if (videometrics.length === 0) {
      // console.log("no videometrics or speaker id")
      setFeatures(valueArrays);
      return;
    }

    //filter speaker metrics from video metrics based on the spkrId
    // const speaker_video_metric = props.videometrics.filter(v => v.student_username === props.spkrId)


    videometrics.forEach((v) => {

      //accumulate each score into their value array
      valueArrays[0].values.push(v.facial_emotion);
      valueArrays[0].time.push(v.time_stamp);
      valueArrays[1].values.push(v.attention_level);
      valueArrays[1].time.push(v.time_stamp);
      valueArrays[2].values.push(v.object_on_focus);
      valueArrays[2].time.push(v.time_stamp);


      facial_emotion_data.push({ time: v.time_stamp, category: v.facial_emotion })
      object_focused_data.push({ time: v.time_stamp, category: v.object_on_focus })

    }
  );


    setFeatures(valueArrays);
    setFacialEmotionDataset(facial_emotion_data)
    setObjectFocusedDataset(object_focused_data)
    setAttentionLevelDataset({ values: valueArrays[1].values, time: valueArrays[1].time })
  },[]);

  useEffect(() => {
    if (props.videometrics.length === 0) return;
    updateGraphs(props.videometrics);
  }, [props.videometrics, updateGraphs]);


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
