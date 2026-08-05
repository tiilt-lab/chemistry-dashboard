import { AppSectionBoxComponent } from "../section-box/section-box-component";
import { AppTimelineSlider } from "../timeline-slider/timeline-slider-component";
import { AppTimeline } from "../../timeline/timeline-component";
import { AppFeaturesComponent } from "../../features/features-component";
import { AppRadarComponent } from "../../radar/radar-component";
import { AppIndividualFeaturesComponent } from "../individualmetrics/features-component";
import { ConceptMapView } from '../concept-map/ConceptMapView';
import SevenCsPanel from '../seven-cs/SevenCsPanel';
import { SevenCsRadarComponent } from '../seven-cs-radar/SevenCsRadarComponent';
import { SessionSelectorComponent } from './SessionSelectorComponent';
import React from "react";
import styles from './infographics-comparison.module.css';

function AppInfographicsComparison(props) {
  // Group mode uses different wrapper to allow full-width layout
  if (props.details === "Group" && props.speakers) {
    return (
      <div className={styles.layoutGrid}>
        {/* ─────────────────────────────────────────────────────────────
            TOP ROW: Discussion Timeline + Session Selector
            ───────────────────────────────────────────────────────────── */}
        <div className={styles.topRow}>
          {/* Discussion Timeline (combined: slider + timeline) - Left */}
          {props.showBoxes.length > 0 && props.showBoxes[1].clicked && (
            <div className={styles.timelineWrapper}>
              <AppSectionBoxComponent type={""} heading={"Discussion Timeline"}>
                <div className={styles.timelineContent}>
                  {/* Timeline Slider */}
                  {props.showBoxes.length > 0 && props.showBoxes[0].clicked && (
                    <div className={styles.timelineSlider}>
                      <AppTimelineSlider id="timeSlider" inputChanged={props.setRange} />
                    </div>
                  )}
                  {/* Timeline Visualization */}
                  <AppTimeline
                    clickedTimeline={props.onClickedTimeline}
                    session={props.session}
                    transcripts={props.displayTranscripts}
                    start={props.startTime}
                    end={props.endTime}
                  />
                </div>
              </AppSectionBoxComponent>
            </div>
          )}

          {/* Session Selector - Right */}
          {props.deviceOptions && props.deviceOptions.length > 0 && (
            <div className={styles.sessionSelectorWrapper}>
              <AppSectionBoxComponent type={""} heading={"Session Selector"}>
                <SessionSelectorComponent
                  deviceOptions={props.deviceOptions}
                  selectedDeviceIds={props.selectedDeviceIds}
                  onDeviceSelectionChange={props.onDeviceSelectionChange}
                  currentSessionDeviceId={props.currentSessionDeviceId}
                />
              </AppSectionBoxComponent>
            </div>
          )}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            MAIN CONTENT: 2-Column Layout
            ───────────────────────────────────────────────────────────── */}
        <div className={styles.mainContent}>
          {/* ═══════════════ LEFT COLUMN ═══════════════ */}
          <div className={styles.leftColumn}>
            {/* Expression and Thinking Style (with LIWC Radar + Line Charts inside) */}
            {props.showBoxes.length > 0 && props.showBoxes[2].clicked && (
              <AppSectionBoxComponent type={""} heading={"Expression and Thinking Style"}>
                <div className={styles.expressionContent}>
                  {/* LIWC Radar Chart */}
                  {props.showBoxes.length > 0 && props.showBoxes[3].clicked && (
                    <div className={styles.liwcRadarSection}>
                      <AppRadarComponent
                        multiSeries={props.multiSeries}
                        selectedDeviceIds={props.selectedDeviceIds}
                        mode={props.details}
                        session={props.session}
                        transcripts={props.displayTranscripts}
                        radarTrigger={props.radarTrigger}
                        start={props.startTime}
                        end={props.endTime}
                        showFeatures={props.showFeatures}
                      />
                    </div>
                  )}

                  {/* Shared Legend - BELOW the radar chart */}
                  {props.multiSeries && props.multiSeries.length > 1 && props.selectedDeviceIds && props.selectedDeviceIds.length > 1 && (
                    <div className={styles.legendSection}>
                      <div className={styles.legendItems}>
                        {props.multiSeries
                          .filter(s => props.selectedDeviceIds.includes(s.id))
                          .map((s, i) => (
                            <div key={s.id} className={styles.legendItem}>
                              <span
                                className={styles.legendColor}
                                style={{ background: ["#0173B2", "#DE8F05", "#029E73", "#CC78BC", "#ECE133", "#56B4E9", "#949494", "#F0E442"][i % 8] }}
                              />
                              <span>{s.label}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Metrics Line Charts */}
                  <div className={styles.metricsSection}>
                    <AppFeaturesComponent
                      multiSeries={props.multiSeries}
                      deviceOptions={props.deviceOptions}
                      selectedDeviceIds={props.selectedDeviceIds}
                      onDeviceSelectionChange={props.onDeviceSelectionChange}
                      currentSessionDeviceId={props.currentSessionDeviceId}
                      session={props.session}
                      transcripts={props.displayTranscripts}
                      showFeatures={props.showFeatures}
                      mode={props.details}
                      hideSessionPicker={true}
                      hideLegend={true}
                    />
                  </div>
                </div>
              </AppSectionBoxComponent>
            )}
          </div>

          {/* ═══════════════ RIGHT COLUMN ═══════════════ */}
          <div className={styles.rightColumn}>
            {/* 7C Collaboration Assessment (combined: radar + cards) */}
            {props.showBoxes.length > 6 && props.showBoxes[6] && props.showBoxes[6].clicked && (
              <AppSectionBoxComponent type={""} heading={"7C Collaboration Assessment"}>
                <div className={styles.sevenCsContent}>
                  {/* 7C Radar Chart */}
                  <div className={styles.sevenCsRadar}>
                    <SevenCsRadarComponent
                      sessionDeviceId={props.sessionDevice?.id}
                      multiSeries={props.multiSeries}
                      selectedDeviceIds={props.selectedDeviceIds}
                      mode={props.details}
                    />
                  </div>
                  {/* 7C Analysis Cards */}
                  <div className={styles.sevenCsCards}>
                    <SevenCsPanel
                      sessionDeviceId={props.sessionDevice?.id}
                      sessionName={props.session?.name || props.session?.discussion_topic}
                      deviceName={props.sessionDevice?.name}
                    />
                  </div>
                </div>
              </AppSectionBoxComponent>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            BOTTOM: Visual Scaffolding (Full Width)
            ───────────────────────────────────────────────────────────── */}
        {props.showBoxes.length > 5 && props.showBoxes[5] && props.showBoxes[5].clicked && (
          <div className={styles.bottomSection}>
            <AppSectionBoxComponent type={""} heading={"Visual Scaffolding"}>
              <ConceptMapView
                sessionId={props.session?.id}
                sessionDeviceId={props.sessionDevice?.id}
              />
            </AppSectionBoxComponent>
          </div>
        )}
      </div>
    );
  }

  // Individual/Comparison modes use original infographics-container layout
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

          {/* ═══════════════════════════════════════════════════════════════
              INDIVIDUAL / COMPARISON MODE: Original Layout
              ═══════════════════════════════════════════════════════════════ */}
          {props.details !== "Group" && (
            <>
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
                    transcripts={props.spkr1Transcripts}
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

              {/* Individual features blocks */}
              {props.showBoxes.length > 0 && props.showBoxes[4].clicked && (
                <AppSectionBoxComponent type={"small-section"} heading={`Participation and Impact Style`}>
                  <AppIndividualFeaturesComponent
                    session={props.session}
                    transcripts={props.displayTranscripts}
                    spkrId={props.selectedSpkrId1}
                    showFeatures={props.showFeatures}
                  />
                </AppSectionBoxComponent>
              )}

              {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[4].clicked && (
                <AppSectionBoxComponent type={"small-section"} heading={`Participation and Impact Style`}>
                  <AppIndividualFeaturesComponent
                    session={props.session}
                    transcripts={props.displayTranscripts}
                    spkrId={props.selectedSpkrId2}
                    showFeatures={props.showFeatures}
                  />
                </AppSectionBoxComponent>
              )}

              {/* Expression and Thinking Style */}
              {props.showBoxes.length > 0 && props.showBoxes[2].clicked && (
                <AppSectionBoxComponent type={"small-section"} heading={"Expression and Thinking Style"}>
                  <AppFeaturesComponent
                    session={props.session}
                    transcripts={props.spkr1Transcripts}
                    showFeatures={props.showFeatures}
                    mode={props.details}
                  />
                </AppSectionBoxComponent>
              )}

              {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[2].clicked && (
                <AppSectionBoxComponent type={"small-section"} heading={`Expression and Thinking Style`}>
                  <AppFeaturesComponent
                    session={props.session}
                    transcripts={props.spkr2Transcripts}
                    showFeatures={props.showFeatures}
                    mode={props.details}
                  />
                </AppSectionBoxComponent>
              )}

              {/* Radar chart */}
              <div className="small-section" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {props.showBoxes.length > 0 && props.showBoxes[3].clicked && (
                  <AppSectionBoxComponent type={"small-section"} heading={"Radar chart"}>
                    <AppRadarComponent
                      mode={props.details}
                      session={props.session}
                      transcripts={props.spkr1Transcripts}
                      radarTrigger={props.radarTrigger}
                      start={props.startTime}
                      end={props.endTime}
                      showFeatures={props.showFeatures}
                    />
                  </AppSectionBoxComponent>
                )}

                {props.details === "Comparison" && props.showBoxes.length > 0 && props.showBoxes[3].clicked && (
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
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}

export { AppInfographicsComparison };
