import { GenericDialogBox } from "../dialog/dialog-component";
import { AppSectionBoxComponent } from "../components/section-box/section-box-component";
import { AppTimelineSlider } from "../components/timeline-slider/timeline-slider-component";
import { AppTimeline } from "../timeline/timeline-component";
import { AppHeatMapComponent } from "../heat-map/heat-map-component";
import { AppFeaturesComponent } from "../features/features-component";
import { AppRadarComponent } from "../radar/radar-component";
import { AppSpinner } from "../spinner/spinner-component";
import { AppSessionToolbar } from "../session-toolbar/session-toolbar-component";
import { AppKeywordsComponent } from "../keywords/keywords-component";
import { Appheader } from "../header/header-component";
import { isLargeScreen } from "../myhooks/custom-hooks";
import { AppInfographicsView } from "../components/infographics-view/infographics-view-component";
import style from "./pod.module.css";
import React from "react";
import Select from 'react-select';
import { AppInfographicsComparison } from "../components/infographics-view/infographics-comparison";
import { AppInfographicsGroup } from "../components/infographics-view/infographics-group";
import { AppInfographicsIndividual } from "../components/infographics-view/infographics-individual";

function PodComponentPages(props) {
  return (
    <>
      <div className="main-container">
        <Appheader
          title={props.sessionDevice.name}
          leftText={false}
          rightText={"Option"}
          rightEnabled={true}
          rightTextClick={() => props.openDialog("Options")}
          nav={props.navigateToSession}
        />
        <div className="relative">
          <div className="toolbar">
            {props.session ? (
              <AppSessionToolbar
                session={props.session}
                closingSession={props.onSessionClosing}
                menus={[
                  { title: "Group", action: () => props.viewGroup() },
                  { title: "Individual", action: () => props.viewIndividual() },
                  { title: "Comparison", action: () => props.viewComparison() },
                ]}
              />
            ) : (
              <></>
            )}
          </div>
          {props.details === "Group" && (
            <div
              className="center-column-container"
            >
              <br />
              <AppInfographicsGroup
                displayTranscripts={props.displayTranscripts}
                endTime={props.endTime}
                fromclient={false}
                onClickedTimeline={props.onClickedTimeline}
                radarTrigger={props.radarTrigger}
                session={props.session}
                sessionDevice={props.sessionDevice}
                setRange={props.setRange}
                showBoxes={props.showBoxes}
                showFeatures={props.showFeatures}
                startTime={props.startTime}
                speakers={props.speakers}
              ></AppInfographicsGroup>
            </div>
          )}
          {props.details === "Comparison" && (
            <div
              className="center-column-container"
            >
              <br />
              <AppInfographicsComparison
                displayTranscripts={props.displayTranscripts}
                endTime={props.endTime}
                fromclient={false}
                onClickedTimeline={props.onClickedTimeline}
                radarTrigger={props.radarTrigger}
                session={props.session}
                sessionDevice={props.sessionDevice}
                setRange={props.setRange}
                showBoxes={props.showBoxes}
                showFeatures={props.showFeatures}
                startTime={props.startTime}
                speakers={props.speakers}
                selectedSpkrId={props.selectedSpkrId}
                setSelectedSpkrId={props.setSelectedSpkrId}
                selectedSpkrId1={props.selectedSpkrId1}
                setSelectedSpkrId1={props.setSelectedSpkrId1}
                selectedSpkrId2={props.selectedSpkrId2}
                setSelectedSpkrId2={props.setSelectedSpkrId2}
                spkr1Transcripts={props.spkr1Transcripts}
                spkr2Transcripts={props.spkr2Transcripts}
              ></AppInfographicsComparison>
            </div>
          )}
          {props.details === "Individual" && (
            <div
              className="center-column-container"
            >
              <br />
              <AppInfographicsIndividual
                displayTranscripts={props.displayTranscripts}
                endTime={props.endTime}
                fromclient={false}
                onClickedTimeline={props.onClickedTimeline}
                radarTrigger={props.radarTrigger}
                session={props.session}
                sessionDevice={props.sessionDevice}
                setRange={props.setRange}
                showBoxes={props.showBoxes}
                showFeatures={props.showFeatures}
                startTime={props.startTime}
                speakers={props.speakers}
                selectedSpkrId={props.selectedSpkrId}
                setSelectedSpkrId={props.setSelectedSpkrId}
                selectedSpkrId1={props.selectedSpkrId1}
                setSelectedSpkrId1={props.setSelectedSpkrId1}
                spkr1Transcripts={props.spkr1Transcripts}
              ></AppInfographicsIndividual>
            </div>
          )}
        </div>
        {props.loading() ? <AppSpinner></AppSpinner> : <></>}
      </div>
      <GenericDialogBox
        show={props.currentForm !== ""}
        optionsCase={props.currentForm == "Options"}
      >
        {props.currentForm === "Transcript" ? (
          <div className={style["dialog-content"]}>
            <div className={style["dialog-heading"]}>Transcript</div>
            <div className={style["dialog-body"]}>
              {props.currentTranscript.transcript}
            </div>
            <div className={style["dialog-button-container"]}>
              <button
                className={`${style["dialog-button"]} ${style["right-button"]}`}
                onClick={props.closeDialog}
              >
                Close
              </button>
              <button
                className={`${style["dialog-button"]} ${style["left-button"]}`}
                onClick={props.seeAllTranscripts}
              >
                View All
              </button>
            </div>
          </div>
        ) : (
          <></>
        )}

        {props.currentForm == "Options" ? (
          <div className={style["dialog-content"]}>
            <div className={style["dialog-heading"]}>Section Boxes</div>
            <div className={style["dialog-dropdown"]}>
              <Select
                options={props.showBoxes}
                value={props.showBoxes.filter((feature) => feature["clicked"])}
                onChange={props.handleCheckBoxes}
              />
            </div>
            <div className={style["dialog-heading"]}>Discussion Features</div>
            <div className={style["dialog-dropdown"]}>
              <Select
                options={props.showFeatures}
                value={props.showFeatures.filter(
                  (feature) => feature["clicked"]
                )}
                onChange={props.handleCheckFeats}
              />
            </div>
            <div className={style["dialog-heading"]}>Device Options</div>
            <button
              className={style["basic-button"]}
              onClick={() => props.openDialog("RemoveDevice")}
            >
              Disconnect Device
            </button>
            <button
              className={style["cancel-button"]}
              onClick={props.closeDialog}
            >
              Cancel
            </button>
          </div>
        ) : (
          <></>
        )}

        {props.currentForm == "RemoveDevice" ? (
          <div className={style["dialog-content"]}>
            <div className={style["dialog-heading"]}>Disconnect Device</div>
            {!props.deleteDeviceToggle ? (
              <React.Fragment>
                <div className={style["dialog-body"]}>
                  Are you sure you want to remove this device?
                </div>
                <div className={style["dialog-body"]}>
                  All data will be saved, but the device will be disconnected
                  from the discussion.
                </div>
              </React.Fragment>
            ) : (
              <></>
            )}

            {props.deleteDeviceToggle ? (
              <React.Fragment>
                <div className={style["dialog-body"]}>
                  Are you sure you want to delete this device?
                </div>
                <div className={style["dialog-body"]}>
                  All data for this device will be lost and the device will be
                  disconnected.
                </div>
              </React.Fragment>
            ) : (
              <></>
            )}
            <label className={style["dc-checkbox"]}>
              Delete device
              <input
                id="cbxDelete"
                type="checkbox"
                checked={props.deleteDeviceToggle}
                value={props.deleteDeviceToggle}
                onChange={() =>
                  props.setDeleteDeviceToggle(!props.deleteDeviceToggle)
                }
              />
              <span className={style["checkmark"]}></span>
            </label>
            <div className={style["dialog-button-container"]}>
              <button
                className={style["basic-button"]}
                onClick={() =>
                  props.removeDeviceFromSession(props.deleteDeviceToggle)
                }
              >
                Confirm
              </button>
              <button
                className={style["cancel-button"]}
                onClick={props.closeDialog}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <></>
        )}
      </GenericDialogBox>
    </>
  );
}

export { PodComponentPages };

/*
<AppSectionBoxComponent heading={"Box 1:"}></AppSectionBoxComponent>

            <AppSectionBoxComponent heading={"Box 2:"}></AppSectionBoxComponent>

            <AppSectionBoxComponent heading={"Box 3:"}></AppSectionBoxComponent>
*/
