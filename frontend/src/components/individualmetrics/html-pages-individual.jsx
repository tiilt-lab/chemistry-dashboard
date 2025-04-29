import style from "./features.module.css";
import { DialogBox } from "../../dialog/dialog-component";
import questIcon from "../../assets/img/question.svg";
import { adjDim } from "../../myhooks/custom-hooks";
import React from "react";

function IndividualFeaturePage(props) {
  return (
    <>
      <div className='w-sm'>
        <table
          className={style["features-table"]}
          style={{ width: adjDim(400) + "px" }}
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
                className={style["score-header"]}
                style={{
                  width: adjDim(59) + "px",
                  "padding-right": adjDim(24) + "px",
                }}
              >
                Score
              </th>
              <th
                className={style["graph-header"]}
                style={{ width: adjDim(74) + "px" }}
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
                        alt="quest"
                        onClick={() => props.getInfo(feature.name)}
                        className={style["info-button"]}
                        src={questIcon}
                      />
                      {feature.name}
                    </td>
                    <td
                      className={style.score}
                      style={{
                        width: adjDim(59) + "px",
                        "padding-right": adjDim(24) + "px",
                      }}
                    >
                      <div
                        className={style.number}
                        style={{ "font-size": adjDim(22) + "px" }}
                      >
                        {Math.round(feature.average)}
                      </div>
                      <div
                        className={
                          feature.trend === 1
                            ? `${style["direction-indicator"]} ${style.positive}`
                            : feature.trend === 0
                            ? `${style["direction-indicator"]} ${style.neutral}`
                            : feature.trend === -1
                            ? `${style["direction-indicator"]} ${style.negative}`
                            : style["direction-indicator"]
                        }
                      ></div>
                    </td>
                    <td>
                      {feature.values.length === 0 ? (
                        <div
                          className={style["no-data-span"]}
                          style={{ width: adjDim(74) + "px" }}
                        ></div>
                      ) : (
                        <></>
                      )}
                      <svg
                        viewBox="0 -0.5 74 39.5"
                        className={style.svg}
                        style={{ width: adjDim(74) + "px" }}
                      >
                        <path
                          d={feature.path}
                          fill="none"
                          className={
                            feature.trend >= 0
                              ? style.positive
                              : feature.trend === -1
                              ? style.negative
                              : ""
                          }
                        ></path>
                      </svg>
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
  );
}

export { IndividualFeaturePage };
