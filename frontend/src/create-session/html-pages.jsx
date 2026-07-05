import React from "react";
import { dlgInput, dlgPrimary, dlgCancel } from "../components/dialog-styles"
import { Appheader } from "../header/header-component";
import { GenericDialogBox } from "../dialog/dialog-component";
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component";
import style from "./create-session.module.css";
import style2 from "../dialog/dialog.module.css";
import openFolderIcon from "../assets/img/open-folder.svg";
import podIcon from "../assets/img/icon-pod.svg";
import LightIcon from "@icons/Light";

// Linear wizard steps (Devices is an out-of-band screen, not numbered).
const STEPS = ["Settings", "Keywords", "TopModels"];
const STEP_LABELS = {
  Settings: "Session settings",
  Keywords: "Keyword list",
  TopModels: "Topic model",
};

const contentWrap =
  "mx-auto flex w-full max-w-lg grow flex-col gap-4 overflow-y-auto px-4 py-6";
const fieldLabel = "mb-1.5 block text-sm font-semibold text-tiilt-ink";
const footerBar = "w-full flex-none border-t border-tiilt-line bg-white";
const footerRow = "mx-auto flex w-full max-w-lg gap-3 px-4 py-4";

function Toggle({ label, checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-tiilt-soft/40"
    >
      <span className="text-sm font-medium text-tiilt-ink">{label}</span>
      <span
        className={`relative inline-flex h-6 w-11 flex-none items-center rounded-full transition ${checked ? "bg-tiilt" : "bg-tiilt-line"}`}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-[#fff] shadow transition ${checked ? "translate-x-[22px]" : "translate-x-0.5"}`}
        />
      </span>
    </button>
  );
}

function StepIndicator({ current }) {
  const idx = STEPS.indexOf(current);
  if (idx < 0) return null;
  return (
    <div className="mx-auto w-full max-w-lg flex-none px-4 pt-4">
      <div className="flex items-center justify-between text-xs font-semibold text-tiilt-muted">
        <span>
          Step {idx + 1} of {STEPS.length}
        </span>
        <span className="text-tiilt-ink">{STEP_LABELS[current]}</span>
      </div>
      <div className="mt-2 flex gap-1.5">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`h-1.5 flex-1 rounded-full transition ${i <= idx ? "bg-tiilt" : "bg-tiilt-line"}`}
          />
        ))}
      </div>
    </div>
  );
}

function EmptyState({ title, subtitle }) {
  return (
    <div className="flex flex-col items-center gap-1.5 py-10 text-center">
      <div className="text-lg font-semibold text-tiilt-ink">{title}</div>
      <div className="max-w-xs text-sm text-tiilt-muted">{subtitle}</div>
    </div>
  );
}

function CreateSessionPage(props) {
  return (
    <>
      <div className="main-container">
        <Appheader
          title={props.pageTitle}
          leftText={false}
          rightText={""}
          rightEnabled={false}
          nav={props.navigateToSessions}
        />
        <StepIndicator current={props.currentMenu} />

        {props.currentMenu === "Settings" ? (
          <React.Fragment>
            <div className={contentWrap}>
              <div>
                <label htmlFor="txtName" className={fieldLabel}>
                  Session name
                </label>
                <input
                  id="txtName"
                  className={dlgInput}
                  defaultValue={props.sessionName}
                  onKeyUp={(event) => props.setSessionName(event.target.value)}
                  maxLength="64"
                  placeholder="Untitled session"
                />
              </div>
              <div>
                <label className={fieldLabel}>Folder</label>
                <button
                  type="button"
                  onClick={() => props.openDialog("Folder", "test")}
                  className="flex h-11 w-full items-center justify-between gap-2 rounded-lg border border-tiilt-line bg-white px-3 text-left text-base text-tiilt-ink transition hover:border-tiilt"
                >
                  <span className="truncate">{props.folderPath || "Home"}</span>
                  <img src={openFolderIcon} alt="" className="h-5 w-5 flex-none" />
                </button>
              </div>
              <div className="divide-y divide-tiilt-line overflow-hidden rounded-lg border border-tiilt-line">
                <Toggle
                  label="Allow participant devices"
                  checked={props.byod}
                  onChange={() => props.setByod(!props.byod)}
                />
                <Toggle
                  label="Analyze session features"
                  checked={props.features}
                  onChange={() => props.setFeatures(!props.features)}
                />
              </div>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgPrimary + " w-full"}
                  onClick={props.goToKeywords}
                >
                  Next
                </button>
              </div>
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}

        {props.currentMenu === "Keywords" ? (
          <React.Fragment>
            <div className={contentWrap}>
              {props.keywordLists && props.keywordLists.length == 0 ? (
                <EmptyState
                  title="No keyword lists"
                  subtitle="Create one below, or continue without keywords."
                />
              ) : (
                <></>
              )}
              {props.keywordLists.map((keywordList, index) => (
                <div
                  key={index}
                  className={
                    JSON.stringify(props.selectedKeywordList) ===
                    JSON.stringify(keywordList)
                      ? `${style["keywords-selected"]} ${style["keyword-list-button"]}`
                      : style["keyword-list-button"]
                  }
                  onClick={() =>
                    props.setSelectedKeywordList(
                      props.selectedKeywordList === keywordList
                        ? null
                        : keywordList
                    )
                  }
                >
                  <div className={style["keyword-list-header"]}>
                    <span className={style.title}>{keywordList.name}</span>
                    <span className={style.date}>
                      {" "}
                      - {props.formatKeywordDate(keywordList.creation_date)}
                    </span>
                  </div>
                  <div className={style["keyword-list-keywords"]}>
                    {keywordList.keywordsText}
                  </div>
                </div>
              ))}
              <button
                className={dlgCancel + " w-full"}
                onClick={props.navigateToKeywordLists}
              >
                + Create keyword list
              </button>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgCancel + " flex-1"}
                  onClick={props.goToSettings}
                >
                  Previous
                </button>
                <button
                  className={dlgPrimary + " flex-1"}
                  onClick={props.goToTopModels}
                >
                  Next
                </button>
              </div>
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}

        {props.currentMenu === "TopModels" ? (
          <React.Fragment>
            <div className={contentWrap}>
              {props.topicModels && props.topicModels.length == 0 ? (
                <EmptyState
                  title="No topic models"
                  subtitle="Create one below, or continue without a topic model."
                />
              ) : (
                <></>
              )}
              {props.topicModels.map((topicModel, index) => (
                <div
                  key={index}
                  className={
                    JSON.stringify(props.selectedTopicModel) ===
                    JSON.stringify(topicModel)
                      ? `${style["keywords-selected"]} ${style["keyword-list-button"]}`
                      : style["keyword-list-button"]
                  }
                  onClick={() =>
                    props.setSelectedTopicModel(
                      props.selectedTopicModel === topicModel
                        ? null
                        : topicModel
                    )
                  }
                >
                  <div className={style["keyword-list-header"]}>
                    <span className={style.title}>{topicModel.name}</span>
                    <span className={style.date}>
                      {" "}
                      - {props.formatKeywordDate(topicModel.creation_date)}
                    </span>
                  </div>
                  <div className={style["keyword-list-keywords"]}>
                    {topicModel.summary}
                  </div>
                </div>
              ))}
              <button
                className={dlgCancel + " w-full"}
                onClick={props.navigateToFileUpload}
              >
                + Create topic model
              </button>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgCancel + " flex-1"}
                  onClick={props.goToKeywords}
                >
                  Previous
                </button>
                <button
                  className={dlgPrimary + " flex-1"}
                  onClick={props.createSession}
                >
                  Start session
                </button>
              </div>
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}

        {props.currentMenu === "Devices" ? (
          <React.Fragment>
            <div className={contentWrap}>
              {props.devices.length === 0 ? (
                <EmptyState
                  title="No devices"
                  subtitle="No participant devices have joined yet."
                />
              ) : (
                <></>
              )}
              {props.devices.length > 0 ? (
                <ul className={style.list}>
                  {props.devices.map((device) => {
                    <li
                      className={
                        props.selectedDevices.includes(device)
                          ? style["selected-pod"]
                          : style["pod-item"]
                      }
                      onClick={() => props.deviceSelected(device)}
                    >
                      <img className={style["pod-icon"]} src={podIcon} />
                      <div className={style["pod-text"]}>{device.name}</div>
                      <div className={style["button-container"]}>
                        <button
                          className={
                            device.blinking
                              ? style["selected-button"]
                              : style["pod-button"]
                          }
                          onClick={(event) => props.blinkPod(event, device)}
                        >
                          <svg
                            x="0"
                            y="0"
                            width="20"
                            height="20"
                            viewBox="0 0 512 512"
                            className={style["light-svg"]}
                          >
                            <LightIcon></LightIcon>
                          </svg>
                        </button>
                      </div>
                    </li>;
                  })}
                </ul>
              ) : (
                <></>
              )}
              <button
                className={dlgCancel + " w-full"}
                onClick={props.onClickSelectAll}
              >
                Select all
              </button>
            </div>
            <div className={footerBar}>
              <div className={footerRow}>
                <button
                  className={dlgCancel + " flex-1"}
                  onClick={props.goToTopModels}
                >
                  Previous
                </button>
                <button
                  className={dlgPrimary + " flex-1"}
                  onClick={props.createSession}
                >
                  Start session
                </button>
              </div>
            </div>
          </React.Fragment>
        ) : (
          <></>
        )}
      </div>

      <GenericDialogBox show={props.currentForm !== ""}>
        {props.currentForm === "Error" ? (
          <div className={style["add-dialog"]}>
            <div className={style2["dialog-heading"]}>Invalid Session</div>
            {props.displayText}
            <button className={dlgCancel} onClick={props.closeDialog}>
              Close
            </button>
          </div>
        ) : (
          <></>
        )}

        {props.currentForm === "Folder" ? (
          <div className={style["dialog-window"]}>
            <div className={style2["dialog-heading"]}>Select Folder</div>
            <AppFolderSelectComponent
              selectableFolders={props.folders}
              setFolderSelect={props.setFolderSelect}
              setBreadCrumbSelect={props.setBreadCrumbSelect}
            />
            {props.folderSelect ? (
              <button
                className={dlgPrimary}
                onClick={() =>
                  props.setFolderLocation(
                    props.folderSelect,
                    props.breadCrumbSelect
                  )
                }
              >
                OK
              </button>
            ) : (
              <></>
            )}
            <button className={dlgCancel} onClick={props.closeDialog}>
              Cancel
            </button>
          </div>
        ) : (
          <></>
        )}
      </GenericDialogBox>
    </>
  );
}

export { CreateSessionPage };
