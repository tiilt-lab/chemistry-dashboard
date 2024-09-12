import { AppSectionBoxComponent } from "components/section-box/section-box-component";
import { AppTimelineSlider } from "components/timeline-slider/timeline-slider-component";
import { AppTimeline } from "timeline/timeline-component";
import { AppFeaturesComponent } from "features/features-component";
import { AppRadarComponent } from "radar/radar-component";
import { AppKeywordsComponent } from "keywords/keywords-component";

import React from "react";

function AppInfographicsView(props) {
  return (
    <>
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
