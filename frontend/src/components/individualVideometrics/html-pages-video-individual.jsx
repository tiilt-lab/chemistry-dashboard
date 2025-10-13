import style from "./video-features.module.css"
import { DialogBox } from "../../dialog/dialog-component"
import questIcon from "../../assets/img/question.svg"
import { adjDim } from "../../myhooks/custom-hooks"
import { Line } from "react-chartjs-2";
import { Chart as ChartJS,CategoryScale,LinearScale, PointElement,LineElement,Title,Tooltip,Legend } from "chart.js/auto";
import React from "react"



function IndividualVideoMetricPage(props) {
    ChartJS.register(CategoryScale,LinearScale,PointElement,LineElement,Title,Tooltip,Legend);
    const emotionMap = {
                        angry: 0,
                        disgust: 1,
                        fear: 2,
                        happy: 3,
                        neutral: 4,
                        surprise: 5,
                        };
    const emotionLabels = Object.keys(emotionMap);
    return (
        <>
            <div className="small-section">
                <table
                    className={style["features-table"]}
                >
                    <thead>
                        <tr>
                            <th
                                className={style["desc-header"]}
                                style={{ width: adjDim(186) + "px" }}
                            >
                                Classifier
                            </th>
                            <th
                                className={style["graph-header"]}
                                style={{ width: adjDim(300) + "px" }}
                            >
                                Graph
                            </th>
                        </tr>
                    </thead>
                    {props.features.length > 0 ? (
                        <tbody>
                            {props.showFeatures
                                .filter((sf) => sf["clicked"])
                                .map((sf) => props.features[sf["value"]])
                                .filter((feature) => feature !== undefined) // Ensure feature is defined
                                .map((feature, index) => (
                                    <tr key={index}>
                                        <td>
                                            <img
                                                alt="information about selected feature"
                                                onClick={() =>
                                                    props.getInfo(feature.name)
                                                }
                                                className={style["info-button"]}
                                                src={questIcon}
                                            />
                                            {feature.name}
                                        </td>

                                        <td>
                                            {feature.values.length === 0 ? (
                                                <div
                                                    className={
                                                        style["no-data-span"]
                                                    }
                                                    style={{
                                                        width:
                                                            adjDim(300) + "px",
                                                    }}
                                                ></div>
                                            ) : (
                                                    feature.name == "Facial Emotions"  ? (
                                                     
                                                    <Line 
                                                    data={{
                                                            labels: feature.time,
                                                            datasets: [{
                                                            data: feature.values.map(e => emotionMap[e]),
                                                            stepped: true,
                                                            borderWidth: 2,
                                                            pointRadius: 0,
                                                            }],
                                                        }}
                                                                                                        
                                                    options={{
                                                                responsive: true,
                                                                plugins: { legend: { display: false }, title: { display: true, text: "Emotion Over Time" } },
                                                                scales: {
                                                                x: { title: { text: "Time (s)", display: true } },
                                                                y: { title: { text: feature.name, display: true } ,
                                                                ticks: {
                                                                        stepSize: 1,
                                                                        callback: (value) => emotionLabels[value] ?? "",
                                                                        },
                                                                min: 0,
                                                                max: emotionLabels.length - 1,
                                                                }},
                                                            }} 
                                                />
                                                    ) : 
                                                    
                                                    (
                                                    feature.name == "Object Focused On" ?(
                                                    <Line 
                                                    data={{
                                                            labels: feature.time,
                                                            datasets: [{
                                                            data: feature.values,
                                                            // stepped: true,
                                                            borderWidth: 2,
                                                            pointRadius: 0,
                                                            }],
                                                        }}
                                                                                                        
                                                    options={{
                                                                responsive: true,
                                                                plugins: { legend: { display: false } },
                                                                scales: {
                                                                x: { title: { text: "Time (s)", display: true } },
                                                                y: { title: { text: feature.name, display: true } },
                                                                },
                                                            }} 
                                                />
                                                    ) :
                                                    (
                                                    <Line 
                                                    data={{
                                                            labels: feature.time,
                                                            datasets: [{
                                                            data: feature.values,
                                                            // stepped: true,
                                                            borderWidth: 2,
                                                            pointRadius: 0,
                                                            }],
                                                        }}
                                                                                                        
                                                    options={{
                                                                responsive: true,
                                                                plugins: { legend: { display: false } },
                                                                scales: {
                                                                x: { title: { text: "Time (s)", display: true } },
                                                                y: { title: { text: feature.name, display: true } },
                                                                },
                                                            }} 
                                                />)
                                                )
                                                
                                            )}
                                        </td>
                                    </tr>
                                ))}
                        </tbody>
                    ) : (
                        <></>
                    )}
                </table>
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
