import React from "react";
import { EmptyState } from "../components/empty-state";
import { dlgWindow, dlgHeading, dlgInput, dlgPrimary, dlgCancel } from "../components/dialog-styles"
import { pageShell, formCard } from "../components/layout-styles"
import { Appheader } from "../header/header-component";
import { GenericDialogBox } from "../dialog/dialog-component";
import { AppFolderSelectComponent } from "../components/folder-select/folder-select-component";
import style from "./create-session.module.css";
import openFolderIcon from "../assets/img/open-folder.svg";
import IconPod from "@icons/IconPod";
import LightIcon from "@icons/Light";

// Single-step creation: name/folder/toggles, then Start session.
// (Keyword lists and topic models moved to post-hoc analysis.)

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

function CreateSessionPage(props) {
  return (
    <>
      <div role="main" className="main-container">
        <Appheader
          title={props.pageTitle}
          leftText={false}
          rightText={""}
          nav={props.navigateToSessions}
        />
        <div className={pageShell}>
        <div className={formCard}>

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
                  onInput={(event) => props.setSessionName(event.target.value)}
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
                  onClick={props.createSession}
                >
                  Start session
                </button>
              </div>
            </div>
            <div className="mx-auto w-full max-w-lg flex-none px-4 pb-4 text-center text-xs text-tiilt-muted">
              Keywords and topic models are chosen later, as part of
              post-hoc analysis on each pod.
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
                      <IconPod className={style["pod-icon"]} aria-hidden="true" />
                      <div className={style["pod-text"]}>{device.name}</div>
                      <div className={style["button-container"]}>
                        <button
                          aria-label={`Blink light on ${device.name || "pod"}`}
                          aria-pressed={!!device.blinking}
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
                  onClick={props.goToSettings}
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
        </div>
      </div>

      <GenericDialogBox onClose={props.closeDialog} show={props.currentForm !== ""}>
        {props.currentForm === "Error" ? (
          <div className={dlgWindow}>
            <div className={dlgHeading}>Invalid Session</div>
            <div className="text-sm text-tiilt-ink">{props.displayText}</div>
            <button className={dlgCancel} onClick={props.closeDialog}>
              Close
            </button>
          </div>
        ) : (
          <></>
        )}

        {props.currentForm === "Folder" ? (
          <div className={dlgWindow}>
            <div className={dlgHeading}>Select folder</div>
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
