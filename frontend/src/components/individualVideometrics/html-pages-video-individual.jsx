import style from "./video-features.module.css"
import { DialogBox } from "../../dialog/dialog-component"
import questIcon from "../../assets/img/question.svg"
import { adjDim } from "../../myhooks/custom-hooks"
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from "chart.js/auto";
import { CategoricalTimeline, CategoricalDistributionChart } from "../graph-visualizations/categorical-data-visualization"
import React from "react"



function IndividualVideoMetricPage(props) {
    ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);
    const emotionMap = {
        angry: 0,
        disgust: 1,
        fear: 2,
        happy: 3,
        neutral: 4,
        surprise: 5,
        sad: 6
    };
    const emotionLabels = Object.keys(emotionMap);

    return (
        <>
            <div className="wide-section">

                {props.facialEmotionDataset.length > 0 && props.features.length >= 1  && (
                    <CategoricalDistributionChart
                        data={props.facialEmotionDataset}
                        totalDuration={0}
                        title = "Facial Emotions"
                        labels= {props.features[0].values}
                        mode="discrete"
                        granularity={1}
                        aggregate="majority"
                        showMode="seconds"
                        showSparkline
                    />
                )}

                {props.objectFocusedDataset.length > 0 && props.features.length >= 3  && (
                    <CategoricalDistributionChart
                        data={props.objectFocusedDataset}
                        totalDuration={0}
                        title = "Object Focused On"
                        labels= {props.features[2].values}
                        mode="discrete"
                        granularity={1}
                        aggregate="majority"
                    />
                )}

                    {props.features.length >= 2 ? (
                        <div className="w-full max-w-5xl mx-auto">
                            <h3 className="text-base font-semibold mb-2">{props.features[1].name} Over Time</h3>
                            <Line
                                        data={{
                                            labels: props.features[1].time,
                                            datasets: [{
                                                data: props.features[1].values,
                                                // stepped: true,
                                                borderWidth: 2,
                                                pointRadius: 0,
                                            }],
                                        }}

                                        options={{
                                            responsive: true,
                                            plugins: { legend: { display: false }, title: { display: true,  } },
                                            scales: {
                                                x: { title: { text: "Time (s)", display: true } },
                                                y: { title: { text: props.features[1].name, display: true } },
                                            },
                                        }}
                                    />
                        </div>
                    ) : (
                        <></>
                    )
                    }
            </div>

            <DialogBox
                itsclass={"add-dialog"}
                heading={props.featureHeader}
                message={props.featureDescription}
                show={props.showFeatureDialog}
                closedialog={props.closeDialog}
            />
        </>
    )
}

export { IndividualVideoMetricPage }
