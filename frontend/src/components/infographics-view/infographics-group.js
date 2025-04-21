import { AppSectionBoxComponent } from "components/section-box/section-box-component";
import { AppTimelineSlider } from "components/timeline-slider/timeline-slider-component";
import { AppTimeline } from "timeline/timeline-component";
import { AppFeaturesComponent } from "features/features-component";
//import { AppIndividualFeaturesComponent } from "frontend\src\individualmetrics\features-component.js"
import { AppRadarComponent } from "radar/radar-component";
import { AppKeywordsComponent } from "keywords/keywords-component";
import style from "byod-join/byod-join.module.css";
import { adjDim, isLargeScreen } from "myhooks/custom-hooks";
import React, { useState } from "react";
import ReactSlider from "react-slider";

function AppInfographicsGroup(props) {
  return (
    <>
      {props.showBoxes.length > 0 && props.showBoxes[0]["clicked"] && (
        <AppSectionBoxComponent heading={"Timeline control"}>
          <AppTimelineSlider id="timeSlider" inputChanged={props.setRange} />
        </AppSectionBoxComponent>
      )}
      {props.speakers && (
        <div
          className="infographics_container"
          style={{
            display: "flex",
            flexDirection: "row",
            flexWrap: "wrap",
            alignItems: "flex-start",
            gap: "10px",
            width: "auto",
            maxWidth: "100%",
            maxHeight: "calc(100vh - 100px)", // Ensures content doesn't exceed viewport
            overflowY: "auto", // Enables internal scrolling
          }}
        >
          <div className={style["comparison-column"]}>
            {props.showBoxes.length > 0 && props.showBoxes[1]["clicked"] && (
              <AppSectionBoxComponent heading={"Discussion timeline"}>
                <AppTimeline
                  clickedTimeline={props.onClickedTimeline}
                  session={props.session}
                  transcripts={props.displayTranscripts}
                  start={props.startTime}
                  end={props.endTime}
                />
              </AppSectionBoxComponent>
            )}

            {props.showBoxes.length > 0 && props.showBoxes[2]["clicked"] && (
              <AppSectionBoxComponent heading={"Keyword detection"}>
                <AppKeywordsComponent
                  session={props.session}
                  sessionDevice={props.sessionDevice}
                  transcripts={props.displayTranscripts}
                  start={props.startTime}
                  end={props.endTime}
                  fromclient={props.fromclient}
                />
              </AppSectionBoxComponent>
            )}

            {props.showBoxes.length > 0 && props.showBoxes[3]["clicked"] && (
              <AppSectionBoxComponent heading={`Expression and Thinking Style`}>
                <AppFeaturesComponent
                  session={props.session}
                  transcripts={props.displayTranscripts}
                  showFeatures={props.showFeatures}
                />
              </AppSectionBoxComponent>
            )}

            {props.showBoxes.length > 0 && props.showBoxes[4]["clicked"] && (
              <AppSectionBoxComponent heading={"Radar chart"}>
                <AppRadarComponent
                  session={props.session}
                  transcripts={props.displayTranscripts}
                  radarTrigger={props.radarTrigger}
                  start={props.startTime}
                  end={props.endTime}
                  showFeatures={props.showFeatures}
                />
              </AppSectionBoxComponent>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export { AppInfographicsGroup };
