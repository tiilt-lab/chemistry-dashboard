import { AppSectionBoxComponent } from "components/section-box/section-box-component";
import { AppTimelineSlider } from "components/timeline-slider/timeline-slider-component";
import { AppTimeline } from "timeline/timeline-component";
import { AppFeaturesComponent } from "features/features-component";
import { AppRadarComponent } from "radar/radar-component";
import { AppKeywordsComponent } from "keywords/keywords-component";
import style from "byod-join/byod-join.module.css";
import { adjDim, isLargeScreen } from "myhooks/custom-hooks";

import React from "react";
import ReactSlider from "react-slider";

function AppInfographicsView(props) {
  return (
    <>
      {props.speakers && (
        <React.Fragment>
          <div>Selected Speaker:</div>
          <select
            id="speaker"
            className={style["dropdown-input"]}
            style={{ width: adjDim(350) + "px" }}
            value={props.selectedSpkrId}
            onChange={(e) =>
              props.setSelectedSpkrId(parseInt(e.target.value, 10))
            }
          >
            <option value="-1">All Speakers</option>
            {props.speakers.map((speaker) => (
              <option value={speaker["id"]}>{speaker["alias"]}</option>
            ))}
          </select>
        </React.Fragment>
      )}
      {props.showBoxes.length > 0 && props.showBoxes[0]["clicked"] && (
        <AppSectionBoxComponent heading={"Timeline control:"}>
          <AppTimelineSlider id="timeSlider" inputChanged={props.setRange} />
        </AppSectionBoxComponent>
      )}

      {props.showBoxes.length > 0 && props.showBoxes[1]["clicked"] && (
        <AppSectionBoxComponent heading={"Discussion timeline:"}>
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
        <AppSectionBoxComponent heading={"Keyword detection:"}>
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
        <AppSectionBoxComponent heading={"Discussion features:"}>
          <AppFeaturesComponent
            session={props.session}
            transcripts={props.displayTranscripts}
            showFeatures={props.showFeatures}
          />
        </AppSectionBoxComponent>
      )}

      {props.showBoxes.length > 0 && props.showBoxes[4]["clicked"] && (
        <AppSectionBoxComponent heading={"Radar chart:"}>
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
    </>
  );
}

export { AppInfographicsView };
