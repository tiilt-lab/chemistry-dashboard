import { AppSectionBoxComponent } from "components/section-box/section-box-component";
import { AppTimelineSlider } from "components/timeline-slider/timeline-slider-component";
import { AppTimeline } from "timeline/timeline-component";
import { AppFeaturesComponent } from "features/features-component";
// import { AppIndividualFeaturesComponent } from "individualmetrics/features-component";
import { AppRadarComponent } from "radar/radar-component";
import { AppKeywordsComponent } from "keywords/keywords-component";
import style from "byod-join/byod-join.module.css";
import { adjDim, isLargeScreen } from "myhooks/custom-hooks";
import {AppIndividualFeaturesComponent} from "individualmetrics/features-component";
import React, { useState } from "react";
import ReactSlider from "react-slider";

function AppInfographicsView(props) {
  const [selectedSpkrId1, setSelectedSpkrId1] = useState(-1);
  const [selectedSpkrId2, setSelectedSpkrId2] = useState(props.speakers?.[0]?.id ?? 1);

  return (
    <>
      {props.speakers && (
        <div
        className="pod_overview-container-large__+DaY+"
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
            
            <select
              id="speaker1"
              className={style["dropdown-input"]}
              style={{ width: adjDim(350) + "px" }}
              value={selectedSpkrId1}
              onChange={(e) =>
                setSelectedSpkrId1(parseInt(e.target.value, 10))
              }
            >
              <option value="-1">Group</option>
              {props.speakers.map((speaker) => (
                <option key={speaker["id"]} value={speaker["id"]}>
                  {speaker["alias"]}
                </option>
              ))}
            </select>

            {selectedSpkrId1 === -1 ? (
              // Content for All Speakers
              <>
                {props.showBoxes.length > 0 && props.showBoxes[3]["clicked"] && (
                  <AppSectionBoxComponent heading={"Discussion features"}>
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
                
              </>
            ) : (
              // Content for specific speaker
              <>
                 /* {props.showBoxes.length > 0 && props.showBoxes[3]["clicked"] && (
                  <AppSectionBoxComponent heading={`Discussion features for Speaker ${selectedSpkrId1}`}>
                    <AppFeaturesComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )} 

                {props.showBoxes.length > 0 && props.showBoxes[4]["clicked"] && (
                  <AppSectionBoxComponent heading={`Radar chart for Speaker ${selectedSpkrId1}`}>
                    <AppRadarComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      radarTrigger={props.radarTrigger}
                      start={props.startTime}
                      end={props.endTime}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )}*/

                {props.showBoxes.length > 0 && props.showBoxes[5]["clicked"] && (
                  <AppSectionBoxComponent heading={`Individual Metrics for Speaker ${selectedSpkrId1}`}>
                    <AppIndividualFeaturesComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )}
              </>
            )}

          </div>

          <div className={style["comparison-column"]}>
            
            <select
              id="speaker2"
              className={style["dropdown-input"]}
              style={{ width: adjDim(350) + "px" }}
              value={selectedSpkrId2}
              onChange={(e) =>
                setSelectedSpkrId2(parseInt(e.target.value, 10))
              }
            >
              <option value="-1">Group</option>
              {props.speakers.map((speaker) => (
                <option key={speaker["id"]} value={speaker["id"]}>
                  {speaker["alias"]}
                </option>
              ))}
            </select>

            

            {selectedSpkrId1 === -1 ? (
              // Content for All Speakers
              <>
                {props.showBoxes.length > 0 && props.showBoxes[3]["clicked"] && (
                  <AppSectionBoxComponent heading={"Discussion features"}>
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
              </>
            ) : (
              // Content for specific speaker
              <>
                 /* {props.showBoxes.length > 0 && props.showBoxes[3]["clicked"] && (
                  <AppSectionBoxComponent heading={`Discussion features for Speaker ${selectedSpkrId1}`}>
                    <AppFeaturesComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )} 

                {props.showBoxes.length > 0 && props.showBoxes[4]["clicked"] && (
                  <AppSectionBoxComponent heading={`Radar chart for Speaker ${selectedSpkrId1}`}>
                    <AppRadarComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      radarTrigger={props.radarTrigger}
                      start={props.startTime}
                      end={props.endTime}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )}*/

                {props.showBoxes.length > 0 && props.showBoxes[5]["clicked"] && (
                  <AppSectionBoxComponent heading={`Individual Metrics for Speaker ${selectedSpkrId1}`}>
                    <AppIndividualFeaturesComponent
                      session={props.session}
                      transcripts={props.displayTranscripts.filter(t => t.speaker_id === selectedSpkrId1)}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export { AppInfographicsView };
