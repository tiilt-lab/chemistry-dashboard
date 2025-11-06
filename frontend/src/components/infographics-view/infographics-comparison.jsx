import { AppSectionBoxComponent } from "../section-box/section-box-component";
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component";
import { AppTimeline } from "../../timeline/timeline-component";
import { AppFeaturesComponent } from "../../features/features-component";
import { AppRadarComponent } from "../../radar/radar-component";
import { AppKeywordsComponent } from "../../keywords/keywords-component";
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component";
import { LLMSupportPanel } from "../../llm-support/LLMSupportPanel";
import { ConceptMapView } from '../concept-map/ConceptMapView';
import React from "react";

function AppInfographicsComparison(props) {
  return (
    <>
      {props.speakers && (
        <div className="infographics-container">
          {/* RESTORED: Original speaker dropdowns for Individual/Comparison modes */}
          {props.details !== "Group" && (
            <div className="flex flex-col @sm:flex-row relative box-border wide-section justify-center my-2 max-h-12">
              <select
                id="speaker1"
                className="dropdown small-section"
                value={props.selectedSpkrId1}
                onChange={(e) => props.setSelectedSpkrId1(parseInt(e.target.value, 10))}
              >
                <option value="-1">Group</option>
                {props.speakers.map((speaker) => (
                  <option key={speaker["id"]} value={speaker["id"]}>
                    {speaker["alias"]}
                  </option>
                ))}
              </select>

              {props.details === "Comparison" && (
                <select
                  id="speaker2"
                  className="dropdown small-section"
                  value={props.selectedSpkrId2}
                  onChange={(e) => props.setSelectedSpkrId2(parseInt(e.target.value, 10))}
                >
                  <option value="-1">Group</option>
                  {props.speakers.map((speaker) => (
                    <option key={speaker["id"]} value={speaker["id"]}>
                      {speaker["alias"]}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* Timeline control */}
          {props.showBoxes.length > 0 && props.showBoxes[0].clicked && (
            <AppSectionBoxComponent type={"wide-section"} heading={"Timeline control"}>
              <AppTimelineSlider id="timeSlider" inputChanged={props.setRange} />
            </AppSectionBoxComponent>
          )}

          {/* Discussion timeline (left / optional right for comparison) */}
          {props.showBoxes.length > 0 && props.showBoxes[1].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Discussion timeline"}>
              <AppTimeline
                clickedTimeline={props.onClickedTimeline}
                session={props.session}
                transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                start={props.startTime}
                end={props.endTime}
              />
            </AppSectionBoxComponent>
          )}

          {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[1].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Discussion timeline"}>
              <AppTimeline
                clickedTimeline={props.onClickedTimeline}
                session={props.session}
                transcripts={props.spkr2Transcripts}
                start={props.startTime}
                end={props.endTime}
              />
            </AppSectionBoxComponent>
          )}

          {/* Keyword detection */}
          {props.showBoxes.length > 0 && props.showBoxes[2].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Keyword detection"}>
              <AppKeywordsComponent
                session={props.session}
                sessionDevice={props.sessionDevice}
                transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                start={props.startTime}
                end={props.endTime}
                fromclient={props.fromclient}
              />
            </AppSectionBoxComponent>
          )}

          {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[2].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Keyword detection"}>
              <AppKeywordsComponent
                session={props.session}
                sessionDevice={props.sessionDevice}
                transcripts={props.spkr2Transcripts}
                start={props.startTime}
                end={props.endTime}
                fromclient={props.fromclient}
              />
            </AppSectionBoxComponent>
          )}

          {/* Individual features blocks */}
          {props.details !== "Group" && props.showBoxes.length > 0 && props.showBoxes[5].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={`Participation and Impact Style`}>
              <AppIndividualFeaturesComponent
                session={props.session}
                transcripts={props.displayTranscripts}
                spkrId={props.selectedSpkrId1}
                showFeatures={props.showFeatures}
              />
            </AppSectionBoxComponent>
          )}

          {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[5].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={`Participation and Impact Style`}>
              <AppIndividualFeaturesComponent
                session={props.session}
                transcripts={props.displayTranscripts}
                spkrId={props.selectedSpkrId2}
                showFeatures={props.showFeatures}
              />
            </AppSectionBoxComponent>
          )}

          {/* Expression and Thinking Style - MODE AWARE */}
          {props.showBoxes.length > 0 && props.showBoxes[3].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Expression and Thinking Style"}>
              <AppFeaturesComponent
                /* Multi-session props ONLY for Group mode */
                multiSeries={props.details === "Group" ? props.multiSeries : undefined}
                deviceOptions={props.details === "Group" ? props.deviceOptions : undefined}
                selectedDeviceIds={props.details === "Group" ? props.selectedDeviceIds : undefined}
                onDeviceSelectionChange={props.details === "Group" ? props.onDeviceSelectionChange : undefined}
                currentSessionDeviceId={props.currentSessionDeviceId}
                /* Original props always passed */
                session={props.session}
                transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                showFeatures={props.showFeatures}
                mode={props.details}
              />
            </AppSectionBoxComponent>
          )}

          {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[3].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={`Expression and Thinking Style`}>
              <AppFeaturesComponent
                session={props.session}
                transcripts={props.spkr2Transcripts}
                showFeatures={props.showFeatures}
                mode={props.details}
              />
            </AppSectionBoxComponent>
          )}

          <div className="small-section" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Radar chart */}
          {props.showBoxes.length > 0 && props.showBoxes[4].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Radar chart"}>
              <AppRadarComponent
                /* Multi-session props for Group mode */
                multiSeries={props.details === "Group" ? props.multiSeries : undefined}
                selectedDeviceIds={props.details === "Group" ? props.selectedDeviceIds : undefined}
                mode={props.details}
                /* Original props */
                session={props.session}
                transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
                radarTrigger={props.radarTrigger}
                start={props.startTime}
                end={props.endTime}
                showFeatures={props.showFeatures}
              />
            </AppSectionBoxComponent>
          )}
          

          
          {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[4].clicked && (
            <AppSectionBoxComponent type={"small-section"} heading={"Radar chart"}>
              <AppRadarComponent
                session={props.session}
                transcripts={props.spkr2Transcripts}
                radarTrigger={props.radarTrigger}
                start={props.startTime}
                end={props.endTime}
                showFeatures={props.showFeatures}
                mode={props.details}
              />
            </AppSectionBoxComponent>
          )}

          {/* LLM Analysis Panel */}
          <AppSectionBoxComponent type={"small-section"} heading={"LLM Analysis"}>
            <LLMSupportPanel
              transcripts={props.details === "Group" ? props.displayTranscripts : props.spkr1Transcripts}
              sessionDevice={props.sessionDevice}
              startTime={props.startTime}
              endTime={props.endTime}
              multiSeries={props.details === "Group" ? props.multiSeries : undefined}
            />
          </AppSectionBoxComponent>
          </div>

          {props.details === "Group" && props.showBoxes.length > 0 && props.showBoxes[6] && props.showBoxes[6].clicked && (
  <AppSectionBoxComponent type={"wide-section"} heading={"Visual Scaffolding"}>
    <ConceptMapView 
      sessionId={props.session?.id}
      sessionDeviceId={props.sessionDevice?.id}
      socketConnection={props.socket}  // Will add socket later
    />
  </AppSectionBoxComponent>
)}

        </div>
      )}
    </>
  );
}

export { AppInfographicsComparison };